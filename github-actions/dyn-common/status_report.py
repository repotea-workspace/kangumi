"""Read-only evidence collection followed by a guarded source status write."""

import json
from datetime import datetime, timezone

from dispatch import generation_description, source_run_url
from github_api import GitHubError, is_source_bot, latest_status, post_status
from source_metadata import SHA, validate_metadata

RECEIPT_PATH = ".github/workflows/dyn-receipt.yml"


def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def execution_ref(metadata):
    source = metadata["source"]
    if source["ref_type"] == "tag":
        return source["ref_name"] + "-" + source["repository"].split("/", 1)[1]
    return source["repository"]


def latest_runs(runs, required, expected_ref):
    selected = {}
    for run in runs:
        path = run.get("path")
        if path not in required or run.get("event") != "push" or run.get("head_branch") != expected_ref:
            continue
        previous = selected.get(path)
        # Distinct run IDs order repeated scheduling; attempts order reruns of
        # the same run. Read current API state, not the delayed event payload.
        if previous is None or (run["id"], run.get("run_attempt", 1)) > (
            previous["id"], previous.get("run_attempt", 1)
        ):
            selected[path] = run
    return selected


def aggregate(selected, required, age_seconds, missing_after_seconds):
    missing = sorted(set(required) - set(selected))
    if missing and age_seconds >= missing_after_seconds:
        return "error", "Required dynamic workflow did not start: " + ", ".join(missing)
    if missing or any(run.get("status") != "completed" for run in selected.values()):
        return "pending", "Dynamic checks queued or running"
    failed = [path for path, run in selected.items() if run.get("conclusion") != "success"]
    if failed:
        return "failure", "Dynamic checks failed, cancelled or skipped: " + ", ".join(sorted(failed))
    return "success", "All required dynamic checks passed"


class StatusReporter:
    def __init__(self, execution_api, source_api, execution_repository, policy,
                 server_url="https://github.com", now=None, summary_url=None):
        self.execution_api = execution_api
        self.source_api = source_api
        self.execution_repository = execution_repository
        self.policy = policy
        self.server_url = server_url.rstrip("/")
        self.now = now or datetime.now(timezone.utc)
        self.summary_url = summary_url

    def metadata(self, execution_sha):
        if not SHA.fullmatch(execution_sha):
            raise ValueError("invalid execution SHA")
        try:
            raw = self.execution_api.file(self.execution_repository, ".github/source.json", execution_sha)
        except GitHubError as error:
            if error.status == 404:
                return None  # Legacy/non-opted-in batches have no trusted receipt.
            raise
        metadata = validate_metadata(json.loads(raw), expected_execution=self.execution_repository)
        source = metadata["source"]
        if source["repository"] != self.policy["repository"]:
            return None  # Another explicitly registered source owns this batch.
        if source["repository_id"] != self.policy["repository_id"]:
            raise ValueError("source repository ID does not match trusted policy")
        return metadata

    def attestation(self, metadata, execution_sha):
        source = metadata["source"]
        status = latest_status(self.source_api, source["repository"], source["sha"],
                               self.policy["dispatch_context"])
        expected_url = f"{self.server_url}/{self.execution_repository}/commit/{execution_sha}"
        if (not status or not is_source_bot(status) or status["state"] != "success"
                or status["target_url"] != expected_url
                or status["description"] != generation_description(source["run_id"], source["run_attempt"])):
            return None
        return status

    def verify_source_run(self, metadata):
        source = metadata["source"]
        run = self.source_api.get(f'/repos/{source["repository"]}/actions/runs/{source["run_id"]}')
        if (run.get("repository", {}).get("id") != source["repository_id"]
                or run.get("head_sha") != source["sha"]
                or run.get("run_attempt") != source["run_attempt"]
                or run.get("path") != source["workflow"]
                or run.get("path") not in self.policy["trigger_workflows"]
                or run.get("event") not in ("push", "workflow_dispatch")):
            raise ValueError("source run does not match its attested identity")
        return run

    def verify_workflows(self, metadata, version):
        source = metadata["source"]
        for workflow in version["workflows"]:
            path = workflow["path"]
            original = self.source_api.file(source["repository"], ".github/dyn-workflows/" + path, source["sha"])
            forwarded = self.execution_api.file(
                self.execution_repository, ".github/workflows/" + path, self.execution_sha
            )
            if original != forwarded:
                raise ValueError("required workflow differs from the attested source revision")

    def report(self, execution_sha):
        metadata = self.metadata(execution_sha)
        if metadata is None:
            return {"execution_sha": execution_sha, "skipped": "unregistered or legacy batch"}
        receipt = self.attestation(metadata, execution_sha)
        if receipt is None:
            return {"execution_sha": execution_sha, "skipped": "no current source-owned dispatch receipt"}
        source = metadata["source"]
        version = self.policy["policies"].get(metadata["policy"])
        if version is None:
            return self.write(metadata, execution_sha, receipt, "error", "Unknown dynamic status policy", [])

        try:
            self.verify_source_run(metadata)
            self.execution_sha = execution_sha
            self.verify_workflows(metadata, version)
        except (ValueError, GitHubError) as error:
            # API authorization/outage failures must fail the receiver, not turn
            # incomplete evidence into a product failure or a green result.
            if isinstance(error, GitHubError) and error.status != 404:
                raise
            return self.write(metadata, execution_sha, receipt, "error", str(error), [])

        required = {".github/workflows/" + item["path"]: item["name"] for item in version["workflows"]}
        runs = list(self.execution_api.pages(
            f"/repos/{self.execution_repository}/actions/runs", key="workflow_runs",
            head_sha=execution_sha, event="push",
        ))
        # The API query is not a trust boundary: validate returned identities.
        runs = [run for run in runs if run.get("head_sha") == execution_sha
                and run.get("head_repository", {}).get("full_name") == self.execution_repository]
        selected = latest_runs(runs, required, execution_ref(metadata))
        if any(run.get("name") != required[path] for path, run in selected.items()):
            return self.write(metadata, execution_sha, receipt, "error", "Required workflow name differs from policy", [])
        commit = self.execution_api.get(f"/repos/{self.execution_repository}/commits/{execution_sha}")
        age = (self.now - timestamp(commit["commit"]["committer"]["date"])).total_seconds()
        state, description = aggregate(selected, required, age, version.get("missing_after_seconds", 600))
        return self.write(metadata, execution_sha, receipt, state, description, list(selected.values()))

    def write(self, metadata, execution_sha, receipt, state, description, runs):
        source = metadata["source"]
        # Re-check after all network reads and under the caller's per-source
        # concurrency lock. An old execution must not overwrite a newer dispatch.
        current = self.attestation(metadata, execution_sha)
        if current is None or current["id"] != receipt["id"]:
            return {"execution_sha": execution_sha, "skipped": "dispatch superseded during evidence collection"}
        if len(runs) == 1:
            target = f'{self.server_url}/{self.execution_repository}/actions/runs/{runs[0]["id"]}'
        else:
            target = self.summary_url or f"{self.server_url}/{self.execution_repository}/commit/{execution_sha}"
        previous = latest_status(self.source_api, source["repository"], source["sha"], self.policy["status_context"])
        body = {"state": state, "description": description[:140], "target_url": target}
        if previous is None or any(previous.get(key) != value for key, value in body.items()):
            post_status(self.source_api, source["repository"], source["sha"], self.policy["status_context"],
                        state, description, target)
        return {"execution_sha": execution_sha, "source_sha": source["sha"], "state": state,
                "description": description, "url": target,
                "runs": [f'{self.server_url}/{self.execution_repository}/actions/runs/{run["id"]}' for run in runs]}
