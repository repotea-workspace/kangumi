"""Source identity, authenticated callback evidence, and rollout compatibility."""

import copy
import json
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError

from github_api import GitHub, GitHubError
from status_config import validate_config
from status_relay import relay, source_report, SourceGitHub, wait_for_source
import test_auto_report as fixtures
import test_protocol as protocol
from test_auto_report import EXECUTION_SHA, SOURCE_SHA
from test_status_config import CONFIG


class RelayTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.AutoReporterTests()
        fixture.setUp()
        self.fixture = fixture
        self.execution, self.source = fixture.execution, fixture.source
        self.repository, self.origin = "executor/dynamic-actions", "Owner/Project"
        self.config = copy.deepcopy(CONFIG)
        self.config["source_reporting"] = [self.origin]
        self.source.values["/repos/Owner/Project"]["default_branch"] = "main"
        self.execution.values["/repos/executor/dynamic-actions"] = {"default_branch": "main"}
        self.execution.files[(self.repository, ".github/dynamic-status.yml", "main")] = json.dumps(self.config).encode()
        self.execution.values["/repos/executor/dynamic-actions/actions/runs/500"] = fixture.execution_run
        self.source.dispatch_workflow = Mock(return_value={"workflow_run_id": 900})
        self.ack = {
            "id": 900, "run_attempt": 1, "event": "workflow_dispatch", "head_branch": "main",
            "display_title": f"Status report · {EXECUTION_SHA} · 800-1",
            "path": ".github/workflows/dynamic-dispatch-status.yml",
            "repository": {"full_name": self.origin}, "head_repository": {"full_name": self.origin},
            "status": "completed", "conclusion": "success",
        }
        self.source.values["/repos/Owner/Project/actions/runs/900"] = self.ack
        self.source.page_values["/repos/Owner/Project/actions/runs/900/attempts/1/jobs"] = [
            {"name": "Report dynamic CI status", "conclusion": "success"},
        ]
        self.event = {"inputs": {"execution_repository": self.repository, "execution_sha": EXECUTION_SHA}}

    def relay(self):
        return relay(self.execution, self.source, self.repository, self.config, "one",
                     EXECUTION_SHA, {"workflow_run": self.fixture.execution_run}, "800-1")

    def report(self, **changes):
        args = dict(execution=self.execution, source=self.source, repository=self.repository,
                    origin=self.origin, event=self.event, server_url="https://github.com",
                    summary_url="https://github.com/Owner/Project/actions/runs/900", reconcile=lambda report: report())
        args.update(changes)
        with patch("auto_report.download_artifact", return_value=self.fixture.archive):
            return source_report(**args)

    def test_enrolled_source_dispatches_exact_default_workflow_and_waits_without_pat_statuses(self):
        result = self.relay()
        self.assertEqual(result["source_report_run_id"], 900)
        args = self.source.dispatch_workflow.call_args.args
        self.assertEqual(args[:3], (self.origin, "dynamic-dispatch-status.yml", "main"))
        self.assertEqual(args[3]["run_id"], "500")
        self.assertNotIn("conclusion", args[3])
        self.assertEqual(self.source.posts, [])

    def test_unenrolled_source_keeps_existing_report_path(self):
        self.config["source_reporting"] = []
        self.assertIsNone(self.relay())
        self.source.dispatch_workflow.assert_not_called()

    def test_source_recomputes_result_and_repairs_non_bot_identity(self):
        self.source.require_source_bot = True
        result = self.report()
        self.assertEqual(result["workflows"][0]["state"], "success")
        self.assertEqual(len(self.source.posts), 1)
        # Same state written by a PAT must be reissued by the source bot.
        self.source.history[(self.origin, SOURCE_SHA)][0]["creator"] = {"login": "owner", "type": "User"}
        self.report()
        self.assertEqual(len(self.source.posts), 2)
        self.source.history[(self.origin, SOURCE_SHA)][0]["creator"] = {"login": "github-actions[bot]", "type": "Bot"}
        self.report()
        self.assertEqual(len(self.source.posts), 2)

    def test_explicit_policy_repairs_aggregate_and_detail_identity_once(self):
        fixture = protocol.ProtocolTests()
        fixture.setUp()
        origin = "owner/project"
        config = dict(self.config, source_reporting=[origin], sources={"project": protocol.POLICY})
        fixture.execution.files[(self.repository, ".github/dynamic-status.yml", "main")] = json.dumps(config).encode()
        fixture.execution.values[f"/repos/{self.repository}"] = {"default_branch": "main"}
        fixture.run["repository"] = {"full_name": self.repository}
        fixture.execution.values[f"/repos/{self.repository}/actions/runs/500"] = fixture.run
        fixture.source.require_source_bot = True
        def report():
            return self.report(execution=fixture.execution, source=fixture.source, origin=origin)
        self.assertEqual(report()["state"], "success")
        count = len(fixture.source.posts)
        self.assertEqual(count, 2)
        self.assertEqual({body["context"] for _, body in fixture.source.posts},
                         {"project/dynamic-checks", "dynamic / checks.yml"})
        for status in fixture.source.history:
            if status["context"] != "project/dynamic-dispatch":
                status["creator"] = {"login": "owner", "type": "User"}
        self.assertEqual(report()["state"], "success")
        self.assertEqual(len(fixture.source.posts), count + 2)
        report()
        self.assertEqual(len(fixture.source.posts), count + 2)

    def test_source_failure_result_is_preserved(self):
        self.fixture.execution_run["conclusion"] = "failure"
        self.assertEqual(self.report()["workflows"][0]["state"], "failure")

    def test_source_rejects_cross_repository_and_unenrolled_requests_before_writes(self):
        with self.assertRaisesRegex(ValueError, "does not belong"):
            self.report(origin="Owner/Other")
        bad = copy.deepcopy(self.event)
        bad["inputs"]["execution_repository"] = "evil/dynamic-actions"
        with self.assertRaisesRegex(ValueError, "invalid source"):
            self.report(event=bad)
        self.config["source_reporting"] = []
        self.execution.files[(self.repository, ".github/dynamic-status.yml", "main")] = json.dumps(self.config).encode()
        with self.assertRaisesRegex(ValueError, "not enabled"):
            self.report()
        self.assertEqual(self.source.posts, [])

    def test_event_rerun_refreshes_stale_listing(self):
        stale = dict(self.fixture.execution_run)
        fresh = dict(stale, run_attempt=2, status="in_progress", conclusion=None)
        self.execution.values["/repos/executor/dynamic-actions/actions/runs/500"] = fresh
        self.event["inputs"].update(run_id="500", run_attempt="2", run_status="in_progress")
        result = self.report()
        self.assertEqual(result["workflows"][0]["state"], "pending")
        self.assertEqual(result["workflows"][0]["run_attempt"], 2)

    def test_forged_run_and_missing_receipt_cannot_write(self):
        self.event["inputs"].update(run_id="500", run_attempt="1", run_status="completed")
        self.execution.values["/repos/executor/dynamic-actions/actions/runs/500"] = dict(self.fixture.execution_run, head_sha="c" * 40)
        with self.assertRaisesRegex(ValueError, "differs"):
            self.report()
        self.assertEqual(self.source.posts, [])
        self.execution.values["/repos/executor/dynamic-actions/actions/runs/500"] = self.fixture.execution_run
        self.source.page_values["/repos/Owner/Project/actions/runs/100/artifacts"] = []
        self.assertIn("not available", self.report()["skipped"])
        self.assertEqual(self.source.posts, [])

    def test_acknowledgment_rejects_failed_or_skipped_job_and_wrong_identity(self):
        for change in ({"conclusion": "failure"}, {"path": ".github/workflows/other.yml"}, {"head_branch": "other"}):
            with self.subTest(change=change):
                self.source.values["/repos/Owner/Project/actions/runs/900"] = dict(self.ack, **change)
                with self.assertRaises((ValueError, RuntimeError)):
                    self.relay()
        self.source.values["/repos/Owner/Project/actions/runs/900"] = self.ack
        self.source.page_values["/repos/Owner/Project/actions/runs/900/attempts/1/jobs"][0]["conclusion"] = "skipped"
        with self.assertRaisesRegex(RuntimeError, "did not successfully"):
            self.relay()

    def test_new_run_placeholder_waits_for_verified_identity(self):
        now = [0]
        pending = dict(self.ack, display_title="Report dynamic CI status", status="queued", conclusion=None)
        with patch.object(self.source, "get", side_effect=[pending, self.ack]):
            result = wait_for_source(self.source, self.origin, EXECUTION_SHA, "800-1", 900, "main",
                                     sleep=lambda seconds: now.__setitem__(0, now[0] + seconds), clock=lambda: now[0])
        self.assertEqual(result, 900)
        self.assertEqual(now[0], 10)

    def test_acknowledgment_waits_and_times_out_visibly(self):
        now = [0]
        def sleep(seconds):
            now[0] += seconds
        self.ack["status"] = "in_progress"
        with self.assertRaises(TimeoutError):
            wait_for_source(self.source, self.origin, EXECUTION_SHA, "800-1", 900, "main",
                            sleep=sleep, clock=lambda: now[0])
        self.assertEqual(now[0], 4200)

    def test_enrollment_must_be_unique_and_owner_allowlisted(self):
        for repos in (["Owner/Project", "owner/project"], ["evil/project"], "Owner/Project"):
            with self.subTest(repos=repos), self.assertRaises(ValueError):
                validate_config(dict(self.config, source_reporting=repos), self.repository)

    def test_source_client_blocks_cross_repository_posts(self):
        client = SourceGitHub("token", "https://api.github.com", self.origin)
        with patch.object(client, "request") as request:
            with self.assertRaises(ValueError):
                client.post("/repos/Owner/Other/statuses/" + SOURCE_SHA, {})
            request.assert_not_called()


class DispatchAPITests(unittest.TestCase):
    def test_dispatch_uses_run_id_api_without_retrying_uncertain_post(self):
        client = GitHub("token")
        with patch("github_api.urlopen", side_effect=URLError("connection lost")) as request:
            with self.assertRaises(GitHubError):
                client.dispatch_workflow("owner/repo", "status.yml", "main", {})
        self.assertEqual(request.call_count, 1)
        self.assertEqual(request.call_args.args[0].get_header("X-github-api-version"), "2026-03-10")


if __name__ == "__main__":
    unittest.main()
