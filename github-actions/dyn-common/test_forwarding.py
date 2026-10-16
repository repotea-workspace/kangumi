"""Regression coverage for the default no-configuration forwarding path."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from dispatch import finish_dispatch, prepare_dispatch
from receiver import group_owners
from source_metadata import checkout_ref
from test_protocol import BOT, ENV, FakeAPI


class AutomaticForwardingTests(unittest.TestCase):
    def test_default_injects_receipt_without_source_status_token(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / ".github"
            (directory / "workflows").mkdir(parents=True)
            sentinel = root / "receipt.yml"
            sentinel.write_text("receipt")
            metadata = prepare_dispatch(None, ENV, {"repository": {"id": 10}},
                                        "executor", "", directory, sentinel)
            self.assertIsNone(metadata["policy"])
            self.assertEqual((directory / "workflows/dyn-receipt.yml").read_text(), "receipt")
            self.assertEqual(checkout_ref(root, ENV["GITHUB_REPOSITORY"]), ENV["GITHUB_SHA"])
            self.assertEqual(checkout_ref(root, ENV["GITHUB_REPOSITORY"], explicit_ref="main"), "main")
            self.assertEqual(checkout_ref(root, "other/repository", explicit_ref="release"), "release")

    def test_auto_status_token_resets_only_same_run_rerun_workflows(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / ".github"
            (directory / "workflows").mkdir(parents=True)
            sentinel = root / "receipt.yml"
            sentinel.write_text("receipt")
            env = dict(ENV, GITHUB_RUN_ATTEMPT="2")
            api = FakeAPI()
            api.history = [
                {
                    "creator": {"login": "receiver", "type": "User"},
                    "context": "dynamic / Checks", "state": "success",
                    "description": "Source run 100, attempt 1: passed",
                    "target_url": "https://github.com/executor/dynamic-actions/actions/runs/500",
                },
                {
                    "creator": {"login": "receiver", "type": "User"},
                    "context": "dynamic / Branch only", "state": "success",
                    "description": "Source run 99, attempt 1: passed",
                    "target_url": "https://github.com/executor/dynamic-actions/actions/runs/499",
                },
                {
                    "creator": BOT, "context": "unrelated/check", "state": "success",
                    "description": "Source run 99, attempt 1: passed", "target_url": "https://example.test",
                },
                {
                    "creator": BOT, "context": "dynamic / Unowned", "state": "success",
                    "description": "different protocol", "target_url": "https://example.test",
                },
            ]
            prepare_dispatch(api, env, {"repository": {"id": 10}},
                             "executor", "", directory, sentinel)
            bodies = [body for _, body in api.posts]
            self.assertEqual([body["context"] for body in bodies], [
                "project/dynamic-dispatch", "dynamic / Checks",
            ])
            self.assertEqual(bodies[0]["state"], "pending")
            self.assertEqual(bodies[1]["state"], "pending")
            self.assertEqual(
                bodies[1]["description"], "Source run 100, attempt 2: queued or running"
            )
            self.assertEqual((directory / "workflows/dyn-receipt.yml").read_text(), "receipt")

    def test_newer_auto_generation_prevents_stale_reset(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / ".github"
            (directory / "workflows").mkdir(parents=True)
            sentinel = root / "receipt.yml"
            sentinel.write_text("receipt")
            api = FakeAPI()
            api.history = [{
                "creator": BOT, "context": "dynamic / Checks", "state": "success",
                "description": "Source run 101, attempt 1: passed",
                "target_url": "https://example.test",
            }]
            with self.assertRaisesRegex(ValueError, "newer source run"):
                prepare_dispatch(api, ENV, {"repository": {"id": 10}},
                                 "executor", "", directory, sentinel)
            self.assertEqual(api.posts, [])

    def test_auto_dispatch_finish_binds_commit_without_finalizing_details(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / ".github"
            (directory / "workflows").mkdir(parents=True)
            sentinel = root / "receipt.yml"
            sentinel.write_text("receipt")
            env = dict(ENV, GITHUB_RUN_ATTEMPT="2")
            api = FakeAPI()
            api.history = [{
                "creator": BOT, "context": "dynamic / Checks", "state": "success",
                "description": "Source run 100, attempt 1: passed",
                "target_url": "https://example.test",
            }]
            metadata = prepare_dispatch(
                api, env, {"repository": {"id": 10}}, "executor", "", directory, sentinel
            )
            finish_dispatch(api, env, metadata, "f" * 40)
            self.assertEqual(api.posts[-1][1]["context"], "project/dynamic-dispatch")
            self.assertEqual(api.posts[-1][1]["state"], "success")
            self.assertTrue(api.posts[-1][1]["target_url"].endswith("/commit/" + "f" * 40))
            self.assertFalse(any(
                body["context"] == "dynamic / Checks" and body["state"] == "success"
                for _, body in api.posts
            ))

    def test_auto_receipt_failure_closes_successful_dispatch_and_pending_details(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / ".github"
            (directory / "workflows").mkdir(parents=True)
            sentinel = root / "receipt.yml"
            sentinel.write_text("receipt")
            env = dict(ENV, GITHUB_RUN_ATTEMPT="2")
            api = FakeAPI()
            api.history = [{
                "creator": BOT, "context": "dynamic / Checks", "state": "success",
                "description": "Source run 100, attempt 1: passed",
                "target_url": "https://example.test",
            }]
            metadata = prepare_dispatch(
                api, env, {"repository": {"id": 10}}, "executor", "", directory, sentinel
            )
            finish_dispatch(api, env, metadata, "f" * 40)
            finish_dispatch(api, env, metadata)
            errors = [body for _, body in api.posts if body["state"] == "error"]
            self.assertEqual(
                [body["context"] for body in errors],
                ["project/dynamic-dispatch", "dynamic / Checks"],
            )
            self.assertEqual(errors[1]["description"],
                             "Source run 100, attempt 2: forwarding failed")

    def test_finish_emits_source_owned_receipt_without_status_permission(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / ".github"
            (directory / "workflows").mkdir(parents=True)
            sentinel = root / "receipt.yml"
            sentinel.write_text("receipt")
            metadata = prepare_dispatch(None, ENV, {"repository": {"id": 10}},
                                        "executor", "", directory, sentinel)
            (directory / "workflows/check.yml").write_text("name: Test\n")
            output = root / "output"
            env = dict(os.environ, **ENV, STATUS_POLICY="", RUNNER_TEMP=str(root),
                       GITHUB_OUTPUT=str(output))
            execution_sha = "f" * 40
            script = Path(__file__).resolve().parent.parent / "dyn-actions/forward.py"
            subprocess.run(["python3", str(script), "finish", "--metadata-dir", str(directory),
                            "--execution-sha", execution_sha], env=env, check=True, capture_output=True)
            receipt_path = output.read_text().strip().split("=", 1)[1]
            self.assertEqual(json.loads(Path(receipt_path).read_text()),
                             {"metadata": metadata, "execution_sha": execution_sha, "workflow_manifest":
                              {".github/workflows/check.yml": hashlib.sha256(b"name: Test\n").hexdigest()}})

    def test_central_group_is_owner_scoped_and_unique(self):
        config = {"schema_version": 1, "execution_repository": "executor/dynamic-actions",
                  "credential_groups": {"one": {"owners": ["Org"]}}}
        self.assertEqual(group_owners(config, "one", "executor/dynamic-actions"), ["org"])
        config["credential_groups"]["two"] = {"owners": ["org"]}
        with self.assertRaises(ValueError):
            group_owners(config, "one", "executor/dynamic-actions")

    def test_explicit_policy_finish_does_not_create_auto_artifact(self):
        script = Path(__file__).resolve().parent.parent / "dyn-actions/forward.py"
        spec = importlib.util.spec_from_file_location("forward_cli", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.dict(os.environ, dict(ENV, STATUS_POLICY="checks-v1", SOURCE_STATUS_TOKEN="token", GITHUB_API_URL="https://api.github.com")), \
             patch.object(module.sys, "argv", ["forward.py", "finish", "--execution-sha", "f" * 40]), \
             patch.object(module, "GitHub"), \
             patch.object(module, "read_metadata", return_value={"policy": "checks-v1"}), \
             patch.object(module, "finish_dispatch") as finish, \
             patch.object(module, "write_outputs") as outputs:
            module.main()
            finish.assert_called_once()
            outputs.assert_not_called()
