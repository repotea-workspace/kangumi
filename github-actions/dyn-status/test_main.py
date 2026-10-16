"""Route mode needs no source secret; event evidence retries are bounded."""

import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

COMMON = Path(__file__).resolve().parent.parent / "dyn-common"
sys.path.insert(0, str(COMMON))
from test_protocol import ENV, EXEC_SHA, FakeAPI
from test_status_config import YAML
from source_metadata import build_metadata

spec = importlib.util.spec_from_file_location("dyn_status_main", Path(__file__).with_name("main.py"))
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)


class MainTests(unittest.TestCase):
    def test_route_mode_never_constructs_a_source_client(self):
        api = FakeAPI()
        metadata = build_metadata(ENV, {"repository": {"id": 10}}, "executor", "")
        api.files[("executor/dynamic-actions", ".github/source.json", EXEC_SHA)] = json.dumps(metadata).encode()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "config.yml"
            config.write_text(YAML)
            event = root / "event.json"
            event.write_text(json.dumps({"inputs": {"execution_sha": EXEC_SHA}}))
            output = root / "output"
            env = {
                "STATUS_CONFIG": str(config), "STATUS_MODE": "route",
                "EXECUTION_READ_TOKEN": "execution-only", "GITHUB_API_URL": "https://api.github.com",
                "GITHUB_EVENT_PATH": str(event), "GITHUB_EVENT_NAME": "workflow_dispatch",
                "GITHUB_REPOSITORY": "executor/dynamic-actions", "GITHUB_OUTPUT": str(output),
            }
            with patch.dict(os.environ, env, clear=True), patch.object(main, "GitHub", return_value=api) as client:
                main.main()
            client.assert_called_once_with("execution-only", "https://api.github.com")
            self.assertIn("secret_name=SOURCE_TOKEN\n", output.read_text())
            self.assertNotIn("execution-only", output.read_text())

    def test_missing_artifact_retries_then_reports(self):
        results = iter([
            {"skipped": "dispatch receipt artifact is not available yet"},
            {"workflows": [{"state": "success"}]},
        ])
        sleeps = []
        result = main.reconcile(lambda: next(results), sleep=sleeps.append, clock=lambda: 0)
        self.assertEqual(sleeps, [10])
        self.assertEqual(result["workflows"][0]["state"], "success")

    def test_missing_artifact_times_out_visibly(self):
        now = [0]
        def sleep(seconds):
            now[0] += seconds
        with self.assertRaises(TimeoutError):
            main.reconcile(lambda: {"skipped": "dispatch receipt artifact is not available yet"},
                           sleep=sleep, clock=lambda: now[0])
        self.assertEqual(now[0], main.RECEIPT_WAIT_SECONDS)

    def test_missing_policy_waits_only_for_its_remaining_grace(self):
        results = iter([
            {"state": "pending", "retry_after_seconds": 11, "retry_reason": "missing_workflow"},
            {"state": "error"},
        ])
        sleeps = []
        self.assertEqual(main.reconcile(lambda: next(results), sleep=sleeps.append, clock=lambda: 0)["state"], "error")
        self.assertEqual(sleeps, [11])

    def test_absent_auto_workflow_has_bounded_discovery_not_failure(self):
        now = [0]
        def sleep(seconds):
            now[0] += seconds
        result = main.reconcile(lambda: {"workflows": [{"status": "not_started"}]},
                                sleep=sleep, clock=lambda: now[0])
        self.assertEqual(now[0], main.RUN_DISCOVERY_SECONDS)
        self.assertEqual(result["workflows"][0]["status"], "not_started")

    def test_absent_auto_workflow_discovered_after_listing_lag(self):
        results = iter([{"workflows": [{"status": "not_started"}]},
                        {"workflows": [{"state": "success"}]}])
        sleeps = []
        result = main.reconcile(lambda: next(results), sleep=sleeps.append, clock=lambda: 0)
        self.assertEqual(sleeps, [10])
        self.assertEqual(result["workflows"][0]["state"], "success")
