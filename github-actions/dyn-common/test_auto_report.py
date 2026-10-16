"""Offline tests for automatic per-workflow status reporting."""

import copy
import hashlib
import io
import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError
from zipfile import ZipFile

from auto_report import (
    AutoStatusReporter,
    download_artifact,
    read_receipt,
    workflow_context,
)
from github_api import GitHubError
from source_metadata import build_metadata


SOURCE_SHA = "a" * 40
EXECUTION_SHA = "b" * 40
WORKFLOW_PATH = ".github/workflows/checks.yml"
WORKFLOW_BYTES = b"name: Checks\non: push\njobs: {}\n"
NOW = datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc)
ENV = {
    "GITHUB_REPOSITORY": "Owner/Project",
    "GITHUB_REPOSITORY_ID": "10",
    "GITHUB_SHA": SOURCE_SHA,
    "GITHUB_REF_TYPE": "branch",
    "GITHUB_REF_NAME": "feature/test",
    "GITHUB_RUN_ID": "100",
    "GITHUB_RUN_ATTEMPT": "1",
    "GITHUB_WORKFLOW_REF": (
        "Owner/Project/.github/workflows/trigger.yml@refs/heads/main"
    ),
    "GITHUB_SERVER_URL": "https://github.com",
    "GITHUB_EVENT_NAME": "push",
}


def archive_for(receipt, extra=None):
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("receipt.json", json.dumps(receipt))
        if extra:
            archive.writestr(extra, b"unexpected")
    return buffer.getvalue()


class FakeAPI:
    def __init__(self):
        self.files = {}
        self.values = {}
        self.page_values = {}
        self.history = {}
        self.posts = []
        self.calls = []

    def file(self, repository, path, ref):
        self.calls.append(("file", repository, path, ref))
        key = (repository, path, ref)
        if key not in self.files:
            raise GitHubError(404, path)
        return self.files[key]

    def get(self, path, **params):
        self.calls.append(("get", path, params))
        return self.values[path]

    def pages(self, path, key=None, **params):
        self.calls.append(("pages", path, key, params))
        return iter(self.page_values.get(path, []))

    def statuses(self, repository, sha):
        self.calls.append(("statuses", repository, sha))
        return iter(self.history.get((repository, sha), []))

    def post(self, path, body):
        self.calls.append(("post", path, body))
        self.posts.append((path, copy.deepcopy(body)))
        repository, sha = path.removeprefix("/repos/").split("/statuses/")
        value = dict(body, id=len(self.posts))
        self.history.setdefault((repository, sha), []).insert(0, value)
        return value


class AutoReporterTests(unittest.TestCase):
    def setUp(self):
        self.metadata = build_metadata(
            ENV, {"repository": {"id": 10}}, "executor", None
        )
        self.manifest = {
            WORKFLOW_PATH: hashlib.sha256(WORKFLOW_BYTES).hexdigest(),
        }
        self.receipt = {
            "metadata": self.metadata,
            "execution_sha": EXECUTION_SHA,
            "workflow_manifest": self.manifest,
        }
        self.archive = archive_for(self.receipt)
        self.execution = FakeAPI()
        self.source = FakeAPI()
        self.execution.files[
            ("executor/dynamic-actions", ".github/source.json", EXECUTION_SHA)
        ] = json.dumps(self.metadata).encode()
        self.execution.files[
            ("executor/dynamic-actions", WORKFLOW_PATH, EXECUTION_SHA)
        ] = WORKFLOW_BYTES
        self.execution.values[
            "/repos/executor/dynamic-actions/contents/.github/workflows"
        ] = [
            {"path": WORKFLOW_PATH, "type": "file"},
            {"path": ".github/workflows/dyn-receipt.yml", "type": "file"},
        ]
        self.source.values["/repos/Owner/Project"] = {
            "id": 10,
            "full_name": "owner/project",
            "owner": {"login": "OWNER"},
        }
        self.source_run = {
            "id": 100,
            "run_attempt": 1,
            "repository": {"id": 10},
            "head_repository": {"id": 10},
            "head_sha": SOURCE_SHA,
            "path": ".github/workflows/trigger.yml",
            "event": "push",
        }
        self.source.values[
            "/repos/Owner/Project/actions/runs/100"
        ] = self.source_run
        self.artifact = {
            "id": 700,
            "name": "dyn-dispatch-100-1",
            "expired": False,
            "expires_at": "2026-10-22T10:00:00Z",
            "workflow_run": {
                "id": 100,
                "repository_id": 10,
                "head_repository_id": 10,
                "head_sha": SOURCE_SHA,
            },
        }
        self.source.page_values[
            "/repos/Owner/Project/actions/runs/100/artifacts"
        ] = [self.artifact]
        self.source.page_values[
            "/repos/Owner/Project/actions/runs"
        ] = [self.source_run]
        self.execution_run = {
            "id": 500,
            "run_attempt": 1,
            "repository": {"full_name": "executor/dynamic-actions"},
            "head_repository": {"full_name": "executor/dynamic-actions"},
            "head_sha": EXECUTION_SHA,
            "head_branch": "Owner/Project",
            "path": WORKFLOW_PATH,
            "event": "push",
            "status": "completed",
            "conclusion": "success",
        }
        self.execution.page_values[
            "/repos/executor/dynamic-actions/actions/runs"
        ] = [self.execution_run]
        self.reporter = self.make_reporter()

    def make_reporter(self, owners=("owner",), archive=None):
        archive = self.archive if archive is None else archive
        return AutoStatusReporter(
            self.execution,
            self.source,
            "executor/dynamic-actions",
            owners,
            now=NOW,
            artifact_downloader=lambda api, repository, artifact_id: archive,
        )

    def test_success_posts_per_workflow_with_direct_run_link(self):
        result = self.reporter.report(EXECUTION_SHA)
        workflow = result["workflows"][0]
        self.assertEqual(workflow["state"], "success")
        self.assertEqual(workflow["context"], "dynamic / Checks")
        self.assertTrue(workflow["url"].endswith("/actions/runs/500"))
        self.assertEqual(len(self.source.posts), 1)
        self.assertIn("Source run 100, attempt 1", self.source.posts[0][1]["description"])

    def test_each_started_workflow_gets_its_own_status(self):
        second_path = ".github/workflows/deploy.yaml"
        second_bytes = b"name: Deploy\non: push\njobs: {}\n"
        self.manifest[second_path] = hashlib.sha256(second_bytes).hexdigest()
        self.receipt["workflow_manifest"] = self.manifest
        self.archive = archive_for(self.receipt)
        self.execution.files[
            ("executor/dynamic-actions", second_path, EXECUTION_SHA)
        ] = second_bytes
        self.execution.values[
            "/repos/executor/dynamic-actions/contents/.github/workflows"
        ].append({"path": second_path, "type": "file"})
        failed = dict(
            self.execution_run,
            id=501,
            path=second_path,
            conclusion="cancelled",
        )
        self.execution.page_values[
            "/repos/executor/dynamic-actions/actions/runs"
        ].append(failed)
        result = self.make_reporter().report(EXECUTION_SHA)
        self.assertEqual(
            {item["context"]: item["state"] for item in result["workflows"]},
            {"dynamic / Checks": "success", "dynamic / Deploy": "failure"},
        )
        self.assertEqual(len(self.source.posts), 2)

    def test_tag_execution_must_use_the_forwarded_tag_ref(self):
        self.metadata = build_metadata(
            dict(ENV, GITHUB_REF_TYPE="tag", GITHUB_REF_NAME="v1.2.3"),
            {"repository": {"id": 10}},
            "executor",
            None,
        )
        self.receipt["metadata"] = self.metadata
        self.archive = archive_for(self.receipt)
        self.execution.files[
            ("executor/dynamic-actions", ".github/source.json", EXECUTION_SHA)
        ] = json.dumps(self.metadata).encode()
        self.execution_run["head_branch"] = "v1.2.3-Project"
        result = self.make_reporter().report(EXECUTION_SHA)
        self.assertEqual(result["workflows"][0]["state"], "success")

    def test_explicit_policy_is_left_to_v1_without_source_access(self):
        self.metadata["policy"] = "checks-v1"
        self.execution.files[
            ("executor/dynamic-actions", ".github/source.json", EXECUTION_SHA)
        ] = json.dumps(self.metadata).encode()
        result = self.reporter.report(EXECUTION_SHA)
        self.assertIn("v1 reporter", result["skipped"])
        self.assertEqual(self.source.calls, [])

    def test_terminal_failures_and_nonterminal_runs(self):
        for status, conclusion, expected in (
            ("completed", "failure", "failure"),
            ("completed", "cancelled", "failure"),
            ("completed", "skipped", "failure"),
            ("completed", "neutral", "failure"),
            ("completed", None, "failure"),
            ("queued", None, "pending"),
            ("in_progress", None, "pending"),
        ):
            with self.subTest(status=status, conclusion=conclusion):
                self.source.posts.clear()
                self.source.history.clear()
                self.execution_run.update(status=status, conclusion=conclusion)
                result = self.reporter.report(EXECUTION_SHA)
                self.assertEqual(result["workflows"][0]["state"], expected)

    def test_wrong_owner_is_skipped_before_any_source_access(self):
        reporter = self.make_reporter(owners=("someone-else",))
        result = reporter.report(EXECUTION_SHA)
        self.assertIn("not allowlisted", result["skipped"])
        self.assertEqual(self.source.calls, [])

    def test_source_repository_and_run_identity_are_verified(self):
        original_repository = copy.deepcopy(self.source.values["/repos/Owner/Project"])
        original_run = copy.deepcopy(self.source_run)
        cases = (
            ("repository", lambda: self.source.values["/repos/Owner/Project"].update(id=11)),
            ("head SHA", lambda: self.source_run.update(head_sha="c" * 40)),
            ("path", lambda: self.source_run.update(path=".github/workflows/other.yml")),
            ("event", lambda: self.source_run.update(event="pull_request")),
            ("repository ID", lambda: self.source_run["repository"].update(id=11)),
            ("head repository ID", lambda: self.source_run["head_repository"].update(id=11)),
        )
        for name, mutate in cases:
            with self.subTest(name=name):
                self.source.values["/repos/Owner/Project"] = copy.deepcopy(original_repository)
                self.source_run.clear()
                self.source_run.update(copy.deepcopy(original_run))
                mutate()
                with self.assertRaises(ValueError):
                    self.reporter.report(EXECUTION_SHA)
                self.assertEqual(self.source.posts, [])

    def test_receipt_forgery_and_workflow_tampering_never_write(self):
        forged = copy.deepcopy(self.receipt)
        forged["execution_sha"] = "c" * 40
        with self.assertRaises(ValueError):
            self.make_reporter(archive=archive_for(forged)).report(EXECUTION_SHA)
        self.execution.files[
            ("executor/dynamic-actions", WORKFLOW_PATH, EXECUTION_SHA)
        ] = b"tampered"
        with self.assertRaises(ValueError):
            self.reporter.report(EXECUTION_SHA)
        self.assertEqual(self.source.posts, [])

    def test_manifest_must_be_the_exact_execution_workflow_set(self):
        self.execution.values[
            "/repos/executor/dynamic-actions/contents/.github/workflows"
        ].append({"path": ".github/workflows/hidden.yml", "type": "file"})
        with self.assertRaises(ValueError):
            self.reporter.report(EXECUTION_SHA)
        self.assertEqual(self.source.posts, [])

    def test_injected_receipt_workflow_is_required_but_never_reported(self):
        listing = self.execution.values[
            "/repos/executor/dynamic-actions/contents/.github/workflows"
        ]
        listing[:] = [entry for entry in listing if entry["path"] !=
                      ".github/workflows/dyn-receipt.yml"]
        with self.assertRaises(ValueError):
            self.reporter.report(EXECUTION_SHA)
        self.assertEqual(self.source.posts, [])

    def test_artifact_must_bind_exact_source_run_and_be_unexpired(self):
        for field, value in (
            ("id", 101),
            ("repository_id", 11),
            ("head_repository_id", 11),
            ("head_sha", "c" * 40),
        ):
            with self.subTest(field=field):
                original = self.artifact["workflow_run"][field]
                self.artifact["workflow_run"][field] = value
                with self.assertRaises(ValueError):
                    self.reporter.report(EXECUTION_SHA)
                self.artifact["workflow_run"][field] = original
        self.artifact["expires_at"] = "2026-10-15T09:59:59Z"
        with self.assertRaises(ValueError):
            self.reporter.report(EXECUTION_SHA)

    def test_missing_artifact_skips_for_scheduled_retry(self):
        self.source.page_values[
            "/repos/Owner/Project/actions/runs/100/artifacts"
        ] = []
        result = self.reporter.report(EXECUTION_SHA)
        self.assertIn("not available yet", result["skipped"])
        self.assertEqual(self.source.posts, [])

    def test_wrong_execution_identity_is_not_treated_as_started(self):
        original = copy.deepcopy(self.execution_run)
        cases = (
            ("sha", {"head_sha": "c" * 40}),
            ("head repository", {"head_repository": {"full_name": "attacker/repo"}}),
            ("event", {"event": "workflow_dispatch"}),
            ("ref", {"head_branch": "attacker/project"}),
            ("path", {"path": ".github/workflows/other.yml"}),
        )
        for name, change in cases:
            with self.subTest(name=name):
                self.execution_run.clear()
                self.execution_run.update(original)
                self.execution_run.update(change)
                result = self.reporter.report(EXECUTION_SHA)
                self.assertEqual(result["workflows"][0]["status"], "not_started")
                self.assertEqual(self.source.posts, [])

    def test_latest_execution_attempt_wins(self):
        earlier = copy.deepcopy(self.execution_run)
        latest = copy.deepcopy(self.execution_run)
        latest.update(run_attempt=2, conclusion="cancelled")
        self.execution.page_values[
            "/repos/executor/dynamic-actions/actions/runs"
        ] = [earlier, latest]
        result = self.reporter.report(EXECUTION_SHA)
        self.assertEqual(result["workflows"][0]["state"], "failure")
        self.assertEqual(result["workflows"][0]["run_attempt"], 2)

    def test_source_rerun_cannot_be_overwritten_by_old_attempt(self):
        self.source_run["run_attempt"] = 2
        result = self.reporter.report(EXECUTION_SHA)
        self.assertIn("rerun", result["skipped"])
        self.assertEqual(self.source.posts, [])

    def test_newer_forwarding_with_artifact_supersedes_old_batch(self):
        newer = copy.deepcopy(self.source_run)
        newer.update(id=101, run_attempt=1)
        self.source.page_values[
            "/repos/Owner/Project/actions/runs"
        ] = [self.source_run, newer]
        self.source.page_values[
            "/repos/Owner/Project/actions/runs/101/artifacts"
        ] = [dict(
            self.artifact,
            id=701,
            name="dyn-dispatch-101-1",
            workflow_run=dict(self.artifact["workflow_run"], id=101),
        )]
        result = self.reporter.report(EXECUTION_SHA)
        self.assertIn("newer source dispatch", result["workflows"][0]["skipped"])
        self.assertEqual(self.source.posts, [])

    def test_newer_status_generation_guards_last_write_race(self):
        self.source.history[("Owner/Project", SOURCE_SHA)] = [{
            "context": "dynamic / Checks",
            "state": "pending",
            "description": "Source run 101, attempt 1: queued or running",
            "target_url": "https://github.com/executor/dynamic-actions/actions/runs/600",
        }]
        result = self.reporter.report(EXECUTION_SHA)
        self.assertIn("newer source generation", result["workflows"][0]["skipped"])
        self.assertEqual(self.source.posts, [])

    def test_invalid_execution_runs_do_not_hide_valid_latest_run(self):
        wrong = copy.deepcopy(self.execution_run)
        wrong.update(id=900, head_branch="wrong/ref", conclusion="failure")
        self.execution.page_values[
            "/repos/executor/dynamic-actions/actions/runs"
        ] = [wrong, self.execution_run]
        result = self.reporter.report(EXECUTION_SHA)
        self.assertEqual(result["workflows"][0]["run_id"], 500)
        self.assertEqual(result["workflows"][0]["state"], "success")

    def test_context_is_stable_and_never_exceeds_github_limit(self):
        path = ".github/workflows/" + "a" * 120 + ".yml"
        first = workflow_context(path)
        self.assertEqual(first, workflow_context(path))
        self.assertEqual(len(first), 100)
        self.assertTrue(first.startswith("dynamic / "))

    def test_zip_must_contain_only_receipt(self):
        with self.assertRaises(ValueError):
            read_receipt(archive_for(self.receipt, extra="other.txt"))

    def test_redirect_download_never_forwards_api_token(self):
        payload = b"zip bytes"

        class Response(io.BytesIO):
            headers = {"Content-Length": str(len(payload))}

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.close()

        class RedirectingOpener:
            def open(self, request, timeout):
                self.request = request
                raise HTTPError(
                    request.full_url,
                    302,
                    "Found",
                    {"Location": "https://objects.example/receipt.zip"},
                    None,
                )

        opener = RedirectingOpener()

        def redirected(request, timeout):
            self.assertEqual(request.full_url, "https://objects.example/receipt.zip")
            self.assertIsNone(request.get_header("Authorization"))
            return Response(payload)

        api = SimpleNamespace(api_url="https://api.github.com", token="secret")
        with patch("auto_report.build_opener", return_value=opener), \
                patch("auto_report.urlopen", side_effect=redirected):
            self.assertEqual(download_artifact(api, "Owner/Project", 700), payload)
        self.assertEqual(opener.request.get_header("Authorization"), "Bearer secret")


if __name__ == "__main__":
    unittest.main()
