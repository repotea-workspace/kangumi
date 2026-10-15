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

from dispatch import prepare_dispatch
from receiver import group_owners
from source_metadata import checkout_ref
from test_protocol import ENV


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
