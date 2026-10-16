"""Terminal events must not depend on a future scheduler tick."""

import copy
from datetime import datetime, timezone
import unittest

from reconciliation import EventExecution
import test_protocol
from test_protocol import EXEC_SHA


class EventReconciliationTests(unittest.TestCase):
    def test_terminal_event_overrides_stale_run_listing(self):
        fixture = test_protocol.ProtocolTests()
        fixture.setUp()
        current = copy.deepcopy(fixture.run)
        current["repository"] = {"full_name": "executor/dynamic-actions"}
        fixture.execution.values["/repos/executor/dynamic-actions/actions/runs/500"] = current
        fixture.execution.runs = [dict(current, status="in_progress", conclusion=None)]
        execution = EventExecution(fixture.execution, "executor/dynamic-actions", current)
        execution.refresh()
        fixture.reporter.execution_api = execution
        result = fixture.reporter.report(EXEC_SHA)
        self.assertEqual(result["state"], "success")
        self.assertEqual(result["workflows"][0]["state"], "success")

    def test_old_start_event_cannot_reset_a_completed_attempt(self):
        fixture = test_protocol.ProtocolTests()
        fixture.setUp()
        current = copy.deepcopy(fixture.run)
        current["repository"] = {"full_name": "executor/dynamic-actions"}
        fixture.execution.values["/repos/executor/dynamic-actions/actions/runs/500"] = current
        execution = EventExecution(fixture.execution, "executor/dynamic-actions",
                                   dict(current, status="in_progress", conclusion=None))
        execution.refresh()
        self.assertEqual(execution.observed["status"], "completed")

    def test_run_identity_mismatch_fails_before_reporting(self):
        fixture = test_protocol.ProtocolTests()
        fixture.setUp()
        current = dict(fixture.run, repository={"full_name": "executor/dynamic-actions"})
        fixture.execution.values["/repos/executor/dynamic-actions/actions/runs/500"] = dict(current, head_sha="c" * 40)
        with self.assertRaises(ValueError):
            EventExecution(fixture.execution, "executor/dynamic-actions", current).refresh()

    def test_missing_required_workflow_requests_event_local_grace_retry(self):
        fixture = test_protocol.ProtocolTests()
        fixture.setUp()
        fixture.execution.runs = []
        fixture.reporter.now = datetime(2026, 10, 15, 10, 9, tzinfo=timezone.utc)
        result = fixture.reporter.report(EXEC_SHA)
        self.assertEqual(result["state"], "pending")
        self.assertEqual(result["retry_reason"], "missing_workflow")
        fixture.reporter.now = datetime(2026, 10, 15, 10, 11, tzinfo=timezone.utc)
        result = fixture.reporter.report(EXEC_SHA)
        self.assertEqual(result["state"], "error")
        self.assertNotIn("retry_after_seconds", result)

    def test_running_required_workflow_does_not_wait_for_completion(self):
        fixture = test_protocol.ProtocolTests()
        fixture.setUp()
        fixture.execution.runs[0].update(status="in_progress", conclusion=None)
        result = fixture.reporter.report(EXEC_SHA)
        self.assertEqual(result["state"], "pending")
        self.assertNotIn("retry_after_seconds", result)

    def test_coalesced_other_completion_refreshes_stale_listing(self):
        fixture = test_protocol.ProtocolTests()
        fixture.setUp()
        other = dict(fixture.run, repository={"full_name": "executor/dynamic-actions"})
        event = dict(other, id=501, path=".github/workflows/dyn-receipt.yml")
        fixture.execution.values["/repos/executor/dynamic-actions/actions/runs/501"] = event
        fixture.execution.values["/repos/executor/dynamic-actions/actions/runs/500"] = other
        fixture.execution.runs = [dict(other, status="in_progress", conclusion=None)]
        execution = EventExecution(fixture.execution, "executor/dynamic-actions", event)
        execution.refresh()
        fixture.reporter.execution_api = execution
        result = fixture.reporter.report(EXEC_SHA)
        self.assertEqual(result["state"], "success")
        self.assertEqual(result["workflows"][0]["state"], "success")
