"""Explicit checks syntax preserves aggregate behavior and old batches."""

import copy
import unittest

from status_policy import load_policy, requested_checks
import test_protocol
from test_protocol import POLICY, EXEC_SHA


class ChecksTests(unittest.TestCase):
    def config(self):
        source = copy.deepcopy(POLICY)
        source["checks"] = {"version": 1, **source.pop("policies")["checks-v1"]}
        return {"schema_version": 1, "execution_repository": "executor/dynamic-actions",
                "sources": {"project": source}}

    def test_new_checks_matches_legacy_required_policy(self):
        config = self.config()
        before = copy.deepcopy(config)
        policy = load_policy(config, "project", "executor/dynamic-actions")
        self.assertEqual(policy["policies"], POLICY["policies"])
        self.assertEqual(config, before)

    def test_new_checks_reports_legacy_batch_success_and_failure(self):
        fixture = test_protocol.ProtocolTests()
        fixture.setUp()
        fixture.reporter.policy = load_policy(self.config(), "project", "executor/dynamic-actions")
        self.assertEqual(fixture.reporter.report(EXEC_SHA)["state"], "success")
        fixture.execution.runs[0]["conclusion"] = "failure"
        self.assertEqual(fixture.reporter.report(EXEC_SHA)["state"], "failure")

    def test_versions_are_strict(self):
        for version in (True, "1", 0, 2, None):
            config = self.config()
            config["sources"]["project"]["checks"]["version"] = version
            with self.subTest(version=version), self.assertRaises(ValueError):
                load_policy(config, "project", "executor/dynamic-actions")

    def test_mixed_and_unknown_fields_rejected(self):
        for key, value in [("policies", POLICY["policies"]), ("unknown", True)]:
            config = self.config()
            target = config["sources"]["project"]
            (target if key == "policies" else target["checks"])[key] = value
            with self.assertRaises(ValueError):
                load_policy(config, "project", "executor/dynamic-actions")

    def test_source_checks_keeps_wire_compatibility(self):
        self.assertEqual(requested_checks("version: 1\n"), "checks-v1")
        self.assertEqual(requested_checks("version: 1", "checks-v1"), "checks-v1")
        self.assertEqual(requested_checks("", "checks-v1"), "checks-v1")
        self.assertEqual(requested_checks(), "")

    def test_invalid_source_declaration_fails_closed(self):
        for raw in ("version: true", "version: 2", 'version: "1"',
                    "version: 1\nversion: 1", "version: 1\nworkflows: []"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                requested_checks(raw)
        with self.assertRaises(ValueError):
            requested_checks("version: 1", "other-policy")
