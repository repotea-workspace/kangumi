"""Notify a source repository; only its own Actions token publishes statuses."""

from pathlib import Path
import tempfile
import time

from github_api import GitHub, GitHubError
from receiver import group_owners, report_group, route_group
from reconciliation import EventExecution
from source_metadata import read_remote_metadata, REPOSITORY, SHA
from status_config import load_config


SOURCE_WORKFLOW = ".github/workflows/dynamic-dispatch-status.yml"


def enrolled(config, repository):
    return repository.lower() in {value.lower() for value in config.get("source_reporting", [])}


def wait_for_source(source, origin, sha, notification, run_id, branch,
                    sleep=time.sleep, clock=time.monotonic):
    if type(run_id) is not int or run_id <= 0:
        raise ValueError("dispatch did not return a source workflow run ID")
    started = clock()
    expected = f"Status report · {sha} · {notification}"
    while clock() - started < 4200:
        try:
            run = source.get(f"/repos/{origin}/actions/runs/{run_id}")
        except GitHubError as error:
            if error.status != 404 or clock() - started >= 120:
                raise
            sleep(10)
            continue
        if (run.get("id") != run_id or run.get("display_title") != expected
                or run.get("path") != SOURCE_WORKFLOW or run.get("event") != "workflow_dispatch"
                or run.get("head_branch") != branch
                or (run.get("repository") or {}).get("full_name", "").lower() != origin.lower()
                or (run.get("head_repository") or {}).get("full_name", "").lower() != origin.lower()):
            raise ValueError("source acknowledgment identity does not match notification")
        if run.get("status") == "completed":
            if run.get("conclusion") != "success":
                raise RuntimeError(f"source status workflow {run_id} finished with {run.get('conclusion')}")
            attempt = run.get("run_attempt")
            if type(attempt) is not int or attempt <= 0:
                raise ValueError("source acknowledgment attempt is invalid")
            jobs = [job for job in source.pages(
                f"/repos/{origin}/actions/runs/{run_id}/attempts/{attempt}/jobs", key="jobs"
            ) if job.get("name") == "Report dynamic CI status"]
            if len(jobs) != 1 or jobs[0].get("conclusion") != "success":
                raise RuntimeError("source workflow did not successfully execute its status reporter")
            return run_id
        sleep(10 if clock() - started < 60 else 30)
    raise TimeoutError("source status workflow did not finish; inspect its run before retrying")


def relay(execution, source, repository, config, group, sha, event, notification):
    owners = group_owners(config, group, repository)
    metadata = read_remote_metadata(execution, repository, sha, expected_execution=repository)
    if metadata is None:
        return None
    origin = metadata["source"]["repository"]
    if origin.split("/", 1)[0].lower() not in owners:
        raise ValueError("source does not belong to selected credential group")
    if not enrolled(config, origin):
        return None
    run = event.get("workflow_run") or {}
    payload = {"execution_repository": repository, "execution_sha": sha, "notification_id": notification}
    if run:
        payload.update(run_id=str(run["id"]), run_attempt=str(run["run_attempt"]), run_status=run["status"])
    branch = source.get(f"/repos/{origin}")["default_branch"]
    dispatched = source.dispatch_workflow(origin, "dynamic-dispatch-status.yml", branch, payload)
    run_id = wait_for_source(source, origin, sha, notification, (dispatched or {}).get("workflow_run_id"), branch)
    return {"execution_sha": sha, "source_repository": origin, "relayed": True, "source_report_run_id": run_id}


class SourceGitHub(GitHub):
    require_source_bot = True

    def __init__(self, token, api_url, repository):
        super().__init__(token, api_url)
        self.repository = repository

    def post(self, path, body):
        if not path.startswith(f"/repos/{self.repository}/statuses/"):
            raise ValueError("source reporter may only write its own commit statuses")
        return super().post(path, body)


def source_report(execution, source, repository, origin, event, server_url, summary_url, reconcile):
    # Repository selection comes from the trusted workflow, never the payload.
    if not REPOSITORY.fullmatch(repository):
        raise ValueError("invalid configured execution repository")
    payload = event.get("inputs") or {}
    sha = payload.get("execution_sha", "")
    if (payload.get("execution_repository") != repository
            or not isinstance(sha, str) or not SHA.fullmatch(sha)):
        raise ValueError("invalid source status notification")
    metadata = read_remote_metadata(execution, repository, sha, expected_execution=repository)
    if metadata is None or metadata["source"]["repository"].lower() != origin.lower():
        raise ValueError("execution does not belong to this source repository")
    default = execution.get(f"/repos/{repository}")["default_branch"]
    # Fetch data only: no checkout or execution of forwarded source code.
    raw = execution.file(repository, ".github/dynamic-status.yml", default)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "config.yml"
        path.write_bytes(raw)
        config = load_config(path)
    route = route_group(execution, repository, config, sha)
    if route.get("matched") != "true" or not enrolled(config, origin):
        raise ValueError("source reporting is not enabled for this repository")
    run_id = payload.get("run_id")
    if run_id:
        attempt, status = payload.get("run_attempt"), payload.get("run_status")
        if (not isinstance(run_id, str) or not run_id.isascii() or not run_id.isdecimal() or int(run_id) <= 0
                or not isinstance(attempt, str) or not attempt.isascii() or not attempt.isdecimal() or int(attempt) <= 0
                or status not in ("in_progress", "completed")):
            raise ValueError("invalid triggering run notification")
        event_run = {"id": int(run_id), "head_sha": sha, "run_attempt": int(attempt), "status": status}
        execution = EventExecution(execution, repository, event_run)

    def report():
        nonlocal execution
        if not isinstance(execution, EventExecution):
            # Manual repair has no triggering event. Pin one observed run so
            # EventExecution also refreshes other listed runs before writing.
            runs = execution.pages(f"/repos/{repository}/actions/runs", key="workflow_runs",
                                   head_sha=sha, event="push")
            current = next(iter(runs), None)
            if current is not None:
                execution = EventExecution(execution, repository, current)
        if isinstance(execution, EventExecution):
            execution.refresh()
        return report_group(execution, source, repository, config, route["group"], sha,
                            server_url, summary_url)

    return reconcile(report)
