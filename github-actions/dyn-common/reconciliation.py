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


class EventExecution:
    """Use the current event run when the repository run listing lags behind."""

    def __init__(self, api, repository, event_run):
        run_id = event_run.get("id")
        attempt = event_run.get("run_attempt")
        if type(run_id) is not int or run_id <= 0 or type(attempt) is not int or attempt <= 0:
            raise ValueError("invalid triggering workflow run")
        self.api = api
        self.repository = repository
        self.event_run = event_run
        self.observed = None

    def __getattr__(self, name):
        return getattr(self.api, name)

    def refresh(self):
        import time

        expected = self.event_run
        deadline = time.monotonic() + 120
        while True:
            current = self.api.get(f"/repos/{self.repository}/actions/runs/{expected['id']}")
            if (current.get("id") != expected["id"]
                    or current.get("head_sha") != expected["head_sha"]
                    or (current.get("repository") or {}).get("full_name") != self.repository
                    or (current.get("head_repository") or {}).get("full_name") != self.repository
                    or type(current.get("run_attempt")) is not int):
                raise ValueError("current workflow run differs from the triggering execution")
            ready = current["run_attempt"] > expected["run_attempt"] or (
                current["run_attempt"] == expected["run_attempt"]
                and (expected.get("status") != "completed" or current.get("status") == "completed")
            )
            if ready:
                self.observed = current
                return
            if time.monotonic() >= deadline:
                raise TimeoutError("workflow API has not observed the event; rerun reconciliation")
            time.sleep(5)

    def pages(self, path, key=None, **params):
        observed = self.observed
        use_observed = (
            observed is not None
            and path == f"/repos/{self.repository}/actions/runs"
            and key == "workflow_runs"
            and params.get("head_sha") == observed["head_sha"]
            and params.get("event") == observed.get("event")
        )
        for run in self.api.pages(path, key=key, **params):
            if (use_observed and run.get("id") == observed["id"]
                    and run.get("run_attempt", 1) <= observed["run_attempt"]):
                continue
            if use_observed:
                current = self.api.get(f"/repos/{self.repository}/actions/runs/{run['id']}")
                # The list endpoint can lag a different, coalesced completion
                # event. Refresh every listed run, including completed runs
                # that might since have been rerun.
                if any(current.get(field) != run.get(field) for field in
                       ("id", "head_sha", "path", "event", "head_branch")):
                    raise ValueError("refreshed workflow run identity differs from its listing")
                if (current.get("repository", {}).get("full_name") != self.repository
                        or current.get("head_repository", {}).get("full_name") != self.repository
                        or type(current.get("run_attempt")) is not int
                        or current["run_attempt"] < run.get("run_attempt", 1)):
                    raise ValueError("refreshed workflow run is stale or from another repository")
                run = current
            yield run
        if use_observed:
            yield observed
