"""Offline protocol tests: fake API evidence, real metadata and reporter paths."""

import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from dispatch import finish_dispatch, finalize_failed_trigger, prepare_dispatch
from github_api import GitHubError
from reconciliation import candidates
from source_metadata import build_metadata, checkout_ref, validate_metadata
from status_policy import load_policy
from status_report import StatusReporter, aggregate, latest_runs, execution_ref

SOURCE_SHA = "a" * 40
EXEC_SHA = "b" * 40
BOT = {"login": "github-actions[bot]", "type": "Bot"}
ENV = {
    "GITHUB_REPOSITORY": "owner/project", "GITHUB_REPOSITORY_ID": "10",
    "GITHUB_SHA": SOURCE_SHA, "GITHUB_REF_TYPE": "branch",
    "GITHUB_REF_NAME": "feature/test", "GITHUB_RUN_ID": "100",
    "GITHUB_RUN_ATTEMPT": "1", "GITHUB_WORKFLOW_REF": "owner/project/.github/workflows/trigger.yml@refs/heads/main",
    "GITHUB_SERVER_URL": "https://github.com", "GITHUB_EVENT_NAME": "push",
}
POLICY = {
    "repository": "owner/project", "repository_id": 10,
    "dispatch_context": "project/dynamic-dispatch", "status_context": "project/dynamic-checks",
    "trigger_workflows": [".github/workflows/trigger.yml"],
    "policies": {"checks-v1": {"workflows": [{"path": "checks.yml", "name": "Checks"}],
                              "missing_after_seconds": 600}},
}


class FakeAPI:
    def __init__(self):
        self.history = []
        self.files = {}
        self.values = {}
        self.runs = []
        self.posts = []
        self.before_status = None

    def statuses(self, repository, sha):
        if self.before_status:
            callback, self.before_status = self.before_status, None
            callback()
        return iter(self.history)

    def post(self, path, body):
        value = dict(body, id=len(self.posts) + 1, creator=BOT)
        self.posts.append((path, body))
        self.history.insert(0, value)
        return value

    def file(self, repository, path, ref):
        key = (repository, path, ref)
        if key not in self.files:
            raise GitHubError(404, path)
        return self.files[key]

    def get(self, path, **params):
        return self.values[path]

    def pages(self, path, key=None, **params):
        return iter(self.runs)


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.metadata = build_metadata(ENV, {"repository": {"id": 10}}, "executor", "checks-v1")
        self.source = FakeAPI()
        self.execution = FakeAPI()
        self.source.history = [{
            "id": 42, "creator": BOT, "state": "success", "context": "project/dynamic-dispatch",
            "description": "Dynamic dispatch: source run 100, attempt 1",
            "target_url": "https://github.com/executor/dynamic-actions/commit/" + EXEC_SHA,
        }]
        self.execution.files[("executor/dynamic-actions", ".github/source.json", EXEC_SHA)] = json.dumps(self.metadata).encode()
        self.execution.files[("executor/dynamic-actions", ".github/workflows/checks.yml", EXEC_SHA)] = b"trusted checks"
        self.source.files[("owner/project", ".github/dyn-workflows/checks.yml", SOURCE_SHA)] = b"trusted checks"
        self.source.values["/repos/owner/project/contents/.github/dyn-workflows"] = [
            {"path": ".github/dyn-workflows/checks.yml", "type": "file"},
        ]
        self.execution.values[
            "/repos/executor/dynamic-actions/contents/.github/workflows"
        ] = [
            {"path": ".github/workflows/checks.yml", "type": "file"},
            {"path": ".github/workflows/dyn-receipt.yml", "type": "file"},
        ]
        self.source.values["/repos/owner/project/actions/runs/100"] = {
            "repository": {"id": 10}, "head_sha": SOURCE_SHA, "run_attempt": 1,
            "path": ".github/workflows/trigger.yml", "event": "push",
        }
        self.execution.values["/repos/executor/dynamic-actions/commits/" + EXEC_SHA] = {
            "commit": {"committer": {"date": "2026-10-15T10:00:00Z"}}
        }
        self.run = {
            "id": 500, "path": ".github/workflows/checks.yml", "name": "Checks",
            "event": "push", "head_branch": "owner/project", "head_sha": EXEC_SHA,
            "head_repository": {"full_name": "executor/dynamic-actions"},
            "status": "completed", "conclusion": "success", "run_attempt": 1,
        }
        self.execution.runs = [self.run]
        self.reporter = StatusReporter(self.execution, self.source, "executor/dynamic-actions",
                                       copy.deepcopy(POLICY), now=datetime(2026, 10, 15, 10, 20, tzinfo=timezone.utc))

    def test_full_sha_and_immutable_checkout(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / ".github"
            folder.mkdir()
            (folder / "source.json").write_text(json.dumps(self.metadata))
            self.assertEqual(checkout_ref(root, "owner/project"), SOURCE_SHA)
            with self.assertRaises(ValueError):
                checkout_ref(root, "owner/project", "main")
            with self.assertRaises(ValueError):
                checkout_ref(root, "attacker/project")

    def test_invalid_metadata_never_falls_back(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / ".github"
            folder.mkdir()
            (folder / "source.json").write_text('{"schema_version": 99}')
            with self.assertRaises(ValueError):
                checkout_ref(root, "owner/project", "main")

    def test_legacy_explicit_ref_preserved(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(checkout_ref(root, "owner/project", "release-v1"), "release-v1")

    def test_short_sha_rejected(self):
        self.metadata["source"]["sha"] = "abc1234"
        with self.assertRaises(ValueError):
            validate_metadata(self.metadata)

    def test_policy_cannot_change_context_or_escape_path(self):
        config = {"schema_version": 1, "execution_repository": "executor/dynamic-actions",
                  "sources": {"project": copy.deepcopy(POLICY)}}
        self.assertEqual(load_policy(config, "project", "executor/dynamic-actions"), POLICY)
        config["sources"]["project"]["policies"]["checks-v1"]["workflows"][0]["path"] = "../checks.yml"
        with self.assertRaises(ValueError):
            load_policy(config, "project", "executor/dynamic-actions")

    def test_success_has_direct_execution_link(self):
        result = self.reporter.report(EXEC_SHA)
        self.assertEqual(result["state"], "success")
        self.assertEqual(result["source_sha"], SOURCE_SHA)
        self.assertTrue(result["url"].endswith("/actions/runs/500"))

    def test_all_non_success_terminal_conclusions_fail(self):
        for conclusion in ("failure", "cancelled", "timed_out", "skipped", "neutral", "action_required", "stale", None):
            self.run["conclusion"] = conclusion
            self.assertEqual(self.reporter.report(EXEC_SHA)["state"], "failure", conclusion)

    def test_rerun_in_progress_resets_success(self):
        self.assertEqual(self.reporter.report(EXEC_SHA)["state"], "success")
        self.run.update(run_attempt=2, status="in_progress", conclusion=None)
        self.assertEqual(self.reporter.report(EXEC_SHA)["state"], "pending")

    def test_latest_attempt_wins_over_delayed_event(self):
        newer = dict(self.run, run_attempt=2, conclusion="failure")
        result = latest_runs([newer, self.run], {self.run["path"]}, "owner/project")
        self.assertEqual(result[self.run["path"]]["conclusion"], "failure")

    def test_missing_workflow_expires(self):
        self.execution.runs = []
        self.assertEqual(self.reporter.report(EXEC_SHA)["state"], "error")
        self.reporter.now = datetime(2026, 10, 15, 10, 1, tzinfo=timezone.utc)
        self.assertEqual(self.reporter.report(EXEC_SHA)["state"], "pending")

    def test_wrong_branch_or_head_cannot_pass(self):
        for field, value in (("head_branch", "victim/project"), ("head_sha", "c" * 40),
                             ("head_repository", {"full_name": "attacker/repo"})):
            with self.subTest(field=field):
                self.execution.runs = [dict(self.run, **{field: value})]
                self.assertEqual(self.reporter.report(EXEC_SHA)["state"], "error")

    def test_forged_receipt_cannot_write(self):
        self.source.history[0]["creator"] = {"login": "attacker", "type": "User"}
        self.assertIn("skipped", self.reporter.report(EXEC_SHA))
        self.assertEqual(self.source.posts, [])

    def test_old_generation_cannot_write(self):
        self.source.history[0]["target_url"] = "https://github.com/executor/dynamic-actions/commit/" + "c" * 40
        self.assertIn("skipped", self.reporter.report(EXEC_SHA))
        self.assertEqual(self.source.posts, [])

    def test_receipt_rechecked_after_evidence(self):
        original = self.execution.get
        def mutate(path, **params):
            self.source.history[0] = dict(self.source.history[0], id=99)
            return original(path, **params)
        self.execution.get = mutate
        self.assertIn("skipped", self.reporter.report(EXEC_SHA))
        self.assertEqual(self.source.posts, [])

    def test_wrong_source_run_is_error(self):
        self.source.values["/repos/owner/project/actions/runs/100"]["head_sha"] = "d" * 40
        self.assertEqual(self.reporter.report(EXEC_SHA)["state"], "error")

    def test_workflow_tampering_is_error(self):
        self.execution.files[("executor/dynamic-actions", ".github/workflows/checks.yml", EXEC_SHA)] = b"echo success"
        self.assertEqual(self.reporter.report(EXEC_SHA)["state"], "error")

    def test_api_outage_never_turns_green(self):
        def outage(*args):
            raise GitHubError(503, "/contents")
        self.source.file = outage
        with self.assertRaises(GitHubError):
            self.reporter.report(EXEC_SHA)
        self.assertEqual(self.source.posts, [])

    def test_unknown_policy_is_error(self):
        self.reporter.policy["policies"] = {}
        self.assertEqual(self.reporter.report(EXEC_SHA)["state"], "error")

    def test_multiple_workflows_require_all_success(self):
        selected = {"a": self.run}
        self.assertEqual(aggregate(selected, {"a", "b"}, 20, 600)[0], "pending")
        selected["b"] = dict(self.run, conclusion="skipped")
        self.assertEqual(aggregate(selected, {"a", "b"}, 20, 600)[0], "failure")

    def test_additional_started_workflow_gets_status_but_not_aggregate_vote(self):
        staging_path = ".github/workflows/staging.yml"
        source_staging_path = ".github/dyn-workflows/staging.yml"
        staging = b"name: Staging\non: push\njobs: {}\n"
        self.source.values[
            "/repos/owner/project/contents/.github/dyn-workflows"
        ].append({"path": source_staging_path, "type": "file"})
        self.execution.values[
            "/repos/executor/dynamic-actions/contents/.github/workflows"
        ].append({"path": staging_path, "type": "file"})
        self.source.files[("owner/project", source_staging_path, SOURCE_SHA)] = staging
        self.execution.files[
            ("executor/dynamic-actions", staging_path, EXEC_SHA)
        ] = staging
        self.execution.runs.append(dict(
            self.run,
            id=501,
            path=staging_path,
            conclusion="failure",
        ))

        result = self.reporter.report(EXEC_SHA)

        self.assertEqual(result["state"], "success")
        self.assertEqual(
            {item["context"]: item["state"] for item in result["workflows"]},
            {"dynamic / checks.yml": "success", "dynamic / Staging": "failure"},
        )
        aggregate_posts = [
            body for _, body in self.source.posts
            if body["context"] == "project/dynamic-checks"
        ]
        self.assertEqual(aggregate_posts[-1]["state"], "success")

    def test_duplicate_report_is_idempotent(self):
        self.reporter.report(EXEC_SHA)
        self.reporter.report(EXEC_SHA)
        # One stable per-workflow status plus the existing aggregate status.
        self.assertEqual(len(self.source.posts), 2)

    def test_prepare_resets_result_and_finish_attests_exact_execution(self):
        self.source.history = []
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / ".github"
            (folder / "workflows").mkdir(parents=True)
            sentinel = Path(root) / "receipt.yml"
            sentinel.write_text("trusted receipt")
            metadata = prepare_dispatch(self.source, ENV, {"repository": {"id": 10}},
                                        "executor", "checks-v1", folder, sentinel)
            self.assertEqual(self.source.history[0]["state"], "pending")
            self.assertEqual((folder / "workflows/dyn-receipt.yml").read_text(), "trusted receipt")
            finish_dispatch(self.source, ENV, metadata, EXEC_SHA)
            self.assertEqual(self.source.history[0]["state"], "success")
            self.assertTrue(self.source.history[0]["target_url"].endswith(EXEC_SHA))

    def test_old_prepare_cannot_reset_new_generation(self):
        self.source.history[0]["description"] = "Dynamic dispatch: source run 101, attempt 1"
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                prepare_dispatch(self.source, ENV, {"repository": {"id": 10}},
                                 "executor", "checks-v1", root, "unused")
        self.assertEqual(self.source.posts, [])

    def test_failure_observer_closes_pre_prepare_failure(self):
        self.source.history = []
        event = {"repository": {"full_name": "owner/project", "id": 10},
                 "workflow_run": {"id": 100, "run_attempt": 1, "head_sha": SOURCE_SHA,
                                  "repository": {"id": 10}, "path": ".github/workflows/trigger.yml",
                                  "status": "completed", "conclusion": "cancelled"}}
        finalize_failed_trigger(self.source, dict(ENV, GITHUB_EVENT_NAME="workflow_run"),
                                event, ".github/workflows/trigger.yml")
        self.assertEqual(len(self.source.posts), 2)
        self.assertTrue(all(body["state"] == "error" for _, body in self.source.posts))

    def test_failure_observer_preserves_successful_dispatch(self):
        event = {"repository": {"full_name": "owner/project", "id": 10},
                 "workflow_run": {"id": 100, "run_attempt": 1, "head_sha": SOURCE_SHA,
                                  "repository": {"id": 10}, "path": ".github/workflows/trigger.yml",
                                  "status": "completed", "conclusion": "cancelled"}}
        finalize_failed_trigger(self.source, dict(ENV, GITHUB_EVENT_NAME="workflow_run"),
                                event, ".github/workflows/trigger.yml")
        self.assertEqual(self.source.posts, [])

    def test_receipt_discovery_keeps_superseded_heads_and_manual_sha(self):
        self.execution.runs = [dict(self.run, path=".github/workflows/dyn-receipt.yml"),
                               dict(self.run, path=".github/workflows/dyn-receipt.yml", head_sha="c" * 40)]
        self.assertEqual(candidates(self.execution, "executor/dynamic-actions",
                                    {}, "schedule"),
                         [EXEC_SHA, "c" * 40])


    def test_event_and_explicit_manual_do_not_scan_history(self):
        def forbidden(*args, **kwargs):
            raise AssertionError("unnecessary historical API scan")
        self.execution.pages = forbidden
        event = {"workflow_run": dict(self.run, repository={"full_name": "executor/dynamic-actions"})}
        self.assertEqual(candidates(self.execution, "executor/dynamic-actions", event, "workflow_run"), [EXEC_SHA])
        self.assertEqual(candidates(self.execution, "executor/dynamic-actions",
                                    {"inputs": {"execution_sha": EXEC_SHA}}, "workflow_dispatch"), [EXEC_SHA])

    def test_tag_metadata_selects_tag_execution(self):
        metadata = build_metadata(dict(ENV, GITHUB_REF_TYPE="tag", GITHUB_REF_NAME="v1.2.3"),
                                  {"repository": {"id": 10}}, "executor", "checks-v1")
        self.assertEqual(execution_ref(metadata), "v1.2.3-project")
        self.assertEqual(latest_runs([self.run], {self.run["path"]}, execution_ref(metadata)), {})
        tag_run = dict(self.run, head_branch="v1.2.3-project")
        self.assertEqual(latest_runs([tag_run], {self.run["path"]}, execution_ref(metadata))[self.run["path"]], tag_run)

    def test_result_context_must_match_source_contract(self):
        config = {"schema_version": 1, "execution_repository": "executor/dynamic-actions",
                  "sources": {"project": copy.deepcopy(POLICY)}}
        config["sources"]["project"]["status_context"] = POLICY["dispatch_context"]
        with self.assertRaises(ValueError):
            load_policy(config, "project", "executor/dynamic-actions")


if __name__ == "__main__":
    unittest.main()
