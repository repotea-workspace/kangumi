"""Discover immutable batches from receipts, including superseded branches."""

from datetime import datetime, timedelta, timezone

from source_metadata import SHA
from status_report import RECEIPT_PATH


def candidates(api, execution_repository, event, event_name, now=None, lookback_hours=48):
    now = now or datetime.now(timezone.utc)
    found = set()
    if event_name == "workflow_run":
        run = event.get("workflow_run") or {}
        if (run.get("repository", {}).get("full_name") != execution_repository
                or run.get("head_repository", {}).get("full_name") != execution_repository):
            raise ValueError("workflow_run is not from this execution repository")
        sha = run.get("head_sha", "")
        if not SHA.fullmatch(sha):
            raise ValueError("invalid workflow_run execution SHA")
        return [sha]
    elif event_name not in ("schedule", "workflow_dispatch"):
        raise ValueError("receiver requires workflow_run, schedule or workflow_dispatch")
    requested = event.get("inputs", {}).get("execution_sha", "")
    if requested:
        if not SHA.fullmatch(requested):
            raise ValueError("manual reconciliation requires a full execution SHA")
        return [requested]
    since = (now - timedelta(hours=lookback_hours)).isoformat()
    # A fixed receipt workflow is injected even when the business YAML is
    # invalid or path-filtered. Its old runs remain discoverable after new pushes.
    for run in api.pages(f"/repos/{execution_repository}/actions/runs", key="workflow_runs",
                         event="push", created=">=" + since):
        if (run.get("path") == RECEIPT_PATH
                and run.get("head_repository", {}).get("full_name") == execution_repository):
            sha = run.get("head_sha", "")
            if not SHA.fullmatch(sha):
                raise ValueError("invalid receipt execution SHA")
            found.add(sha)
    return sorted(found)
