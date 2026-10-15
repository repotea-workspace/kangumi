"""Automatic per-workflow statuses backed by source-owned dispatch receipts."""

import hashlib
import io
import json
import re
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen
from zipfile import BadZipFile, ZipFile

from github_api import GitHubError, latest_status, post_status
from source_metadata import SHA, validate_metadata
from status_report import RECEIPT_PATH, execution_ref


ARTIFACT_LIMIT = 2 * 1024 * 1024
RECEIPT_LIMIT = 256 * 1024
WORKFLOW_PATH = re.compile(r"^\.github/workflows/([^/\\\r\n]+\.ya?ml)$")
MANIFEST_DIGEST = re.compile(r"^[0-9a-f]{64}$")
GENERATION = re.compile(r"^Source run (\d+), attempt (\d+):")


class Superseded(RuntimeError):
    """The source run or dispatch was replaced while evidence was collected."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def _read_limited(response, limit):
    length = response.headers.get("Content-Length")
    if length is not None:
        try:
            if int(length) > limit:
                raise ValueError("dispatch receipt artifact is too large")
        except ValueError:
            if str(length).isdigit():
                raise
    chunks = []
    total = 0
    while True:
        chunk = response.read(min(64 * 1024, limit + 1 - total))
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)
        total += len(chunk)
        if total > limit:
            raise ValueError("dispatch receipt artifact is too large")


def download_artifact(api, repository, artifact_id, max_bytes=ARTIFACT_LIMIT):
    """Download an artifact without sending the API token to its redirect target."""
    if type(artifact_id) is not int or artifact_id <= 0:
        raise ValueError("invalid artifact ID")
    path = f"/repos/{repository}/actions/artifacts/{artifact_id}/zip"
    url = api.api_url.rstrip("/") + path
    request = Request(url, headers={
        "Authorization": f"Bearer {api.token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "kangumi-dyn-status",
    })
    opener = build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=30) as response:
            return _read_limited(response, max_bytes)
    except HTTPError as error:
        if error.code not in (301, 302, 303, 307, 308):
            error.close()
            raise GitHubError(error.code, path) from None
        location = error.headers.get("Location")
        error.close()
    except (URLError, TimeoutError):
        raise GitHubError("unavailable", path) from None

    if not location:
        raise GitHubError("invalid-redirect", path)
    target = urljoin(url, location)
    parsed = urlsplit(target)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.fragment:
        raise GitHubError("invalid-redirect", path)
    redirected = Request(target, headers={
        "Accept": "application/zip",
        "User-Agent": "kangumi-dyn-status",
    })
    try:
        with urlopen(redirected, timeout=30) as response:
            return _read_limited(response, max_bytes)
    except HTTPError as error:
        raise GitHubError(error.code, path) from None
    except (URLError, TimeoutError):
        raise GitHubError("unavailable", path) from None


def _object_without_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _load_json(raw, description):
    try:
        return json.loads(raw, object_pairs_hook=_object_without_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid {description}") from error


def read_receipt(archive):
    if not isinstance(archive, bytes) or len(archive) > ARTIFACT_LIMIT:
        raise ValueError("dispatch receipt artifact is too large")
    try:
        with ZipFile(io.BytesIO(archive)) as zipped:
            entries = zipped.infolist()
            if len(entries) != 1 or entries[0].filename != "receipt.json" or entries[0].is_dir():
                raise ValueError("dispatch receipt artifact must contain only receipt.json")
            entry = entries[0]
            if entry.flag_bits & 1 or entry.file_size > RECEIPT_LIMIT:
                raise ValueError("dispatch receipt is invalid or too large")
            with zipped.open(entry) as stream:
                raw = stream.read(RECEIPT_LIMIT + 1)
            if len(raw) > RECEIPT_LIMIT:
                raise ValueError("dispatch receipt is too large")
    except BadZipFile as error:
        raise ValueError("invalid dispatch receipt artifact") from error
    return _load_json(raw, "dispatch receipt")


def validate_receipt(receipt, metadata, execution_sha):
    if not isinstance(receipt, dict) or set(receipt) != {
        "metadata", "execution_sha", "workflow_manifest"
    }:
        raise ValueError("invalid dispatch receipt fields")
    if receipt["metadata"] != metadata or receipt["execution_sha"] != execution_sha:
        raise ValueError("dispatch receipt does not match the forwarded execution")
    manifest = receipt["workflow_manifest"]
    if not isinstance(manifest, dict):
        raise ValueError("invalid workflow manifest")
    for path, digest in manifest.items():
        if not isinstance(path, str) or not WORKFLOW_PATH.fullmatch(path) or path == RECEIPT_PATH:
            raise ValueError("workflow manifest requires flat YAML workflow paths")
        if not isinstance(digest, str) or not MANIFEST_DIGEST.fullmatch(digest):
            raise ValueError("invalid workflow manifest digest")
    return manifest


def workflow_context(path):
    match = WORKFLOW_PATH.fullmatch(path)
    if not match or path == RECEIPT_PATH:
        raise ValueError("invalid workflow path")
    context = "dynamic/" + match.group(1)
    if len(context) <= 100:
        return context
    suffix = "-" + hashlib.sha256(context.encode()).hexdigest()[:12]
    return context[:100 - len(suffix)] + suffix


def _status_description(source, state, conclusion):
    if state == "pending":
        result = "queued or running"
    elif state == "success":
        result = "passed"
    else:
        result = "failed (" + (conclusion or "unknown") + ")"
    return f'Source run {source["run_id"]}, attempt {source["run_attempt"]}: {result}'


def _generation(value):
    match = GENERATION.match(value or "")
    return tuple(map(int, match.groups())) if match else None


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("artifact expiry is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("invalid artifact expiry") from error
    if parsed.tzinfo is None:
        raise ValueError("artifact expiry must include a timezone")
    return parsed


class AutoStatusReporter:
    def __init__(self, execution_api, source_api, execution_repository, owners,
                 server_url="https://github.com", now=None, artifact_downloader=None):
        if isinstance(owners, str):
            raise ValueError("trusted owners must be a collection")
        self.owners = set()
        for owner in owners:
            if not isinstance(owner, str) or not owner or "/" in owner or "\n" in owner or "\r" in owner:
                raise ValueError("invalid trusted source owner")
            self.owners.add(owner.casefold())
        self.execution_api = execution_api
        self.source_api = source_api
        self.execution_repository = execution_repository
        self.server_url = server_url.rstrip("/")
        self.now = now or datetime.now(timezone.utc)
        self.artifact_downloader = artifact_downloader or download_artifact

    def metadata(self, execution_sha):
        if not SHA.fullmatch(execution_sha):
            raise ValueError("invalid execution SHA")
        try:
            raw = self.execution_api.file(
                self.execution_repository, ".github/source.json", execution_sha
            )
        except GitHubError as error:
            if error.status == 404:
                return None
            raise
        if len(raw) > RECEIPT_LIMIT:
            raise ValueError("dynamic source metadata is too large")
        return validate_metadata(
            _load_json(raw, "dynamic source metadata"),
            expected_execution=self.execution_repository,
        )

    def _verify_repository(self, metadata):
        source = metadata["source"]
        repository = self.source_api.get(f'/repos/{source["repository"]}')
        owner = repository.get("owner") or {}
        if (repository.get("id") != source["repository_id"]
                or str(repository.get("full_name", "")).casefold() != source["repository"].casefold()
                or str(owner.get("login", "")).casefold()
                != source["repository"].split("/", 1)[0].casefold()):
            raise ValueError("source repository identity does not match metadata")
        return repository

    def _verify_source_run(self, metadata):
        source = metadata["source"]
        run = self.source_api.get(
            f'/repos/{source["repository"]}/actions/runs/{source["run_id"]}'
        )
        actual_attempt = run.get("run_attempt")
        if (run.get("id") == source["run_id"] and type(actual_attempt) is int
                and actual_attempt > source["run_attempt"]):
            raise Superseded("source run was rerun")
        repository = run.get("repository") or {}
        head_repository = run.get("head_repository") or {}
        if (run.get("id") != source["run_id"]
                or repository.get("id") != source["repository_id"]
                or head_repository.get("id") != source["repository_id"]
                or run.get("head_sha") != source["sha"]
                or actual_attempt != source["run_attempt"]
                or run.get("path") != source["workflow"]
                or run.get("event") not in ("push", "workflow_dispatch")):
            raise ValueError("source run does not match dispatch metadata")
        return run

    def _artifact(self, metadata, run_id=None, run_attempt=None):
        source = metadata["source"]
        run_id = run_id or source["run_id"]
        run_attempt = run_attempt or source["run_attempt"]
        name = f"dyn-dispatch-{run_id}-{run_attempt}"
        matches = [
            artifact for artifact in self.source_api.pages(
                f'/repos/{source["repository"]}/actions/runs/{run_id}/artifacts',
                key="artifacts",
            )
            if artifact.get("name") == name
        ]
        if not matches:
            return None
        if len(matches) != 1:
            raise ValueError("dispatch receipt artifact is not unique")
        artifact = matches[0]
        workflow_run = artifact.get("workflow_run") or {}
        if (type(artifact.get("id")) is not int or artifact["id"] <= 0
                or artifact.get("expired") is not False
                or _timestamp(artifact.get("expires_at")) <= self.now
                or workflow_run.get("id") != run_id
                or workflow_run.get("repository_id") != source["repository_id"]
                or workflow_run.get("head_repository_id") != source["repository_id"]
                or workflow_run.get("head_sha") != source["sha"]):
            raise ValueError("dispatch receipt artifact identity is invalid")
        return artifact

    def _verify_workflow_manifest(self, manifest, execution_sha):
        listing = self.execution_api.get(
            f"/repos/{self.execution_repository}/contents/.github/workflows",
            ref=execution_sha,
        )
        if not isinstance(listing, list):
            raise ValueError("execution workflow directory is invalid")
        actual = set()
        receipt_seen = False
        for entry in listing:
            path = entry.get("path", "")
            if path == RECEIPT_PATH:
                if receipt_seen or entry.get("type") != "file":
                    raise ValueError("execution receipt workflow is invalid")
                receipt_seen = True
                continue
            if WORKFLOW_PATH.fullmatch(path):
                if entry.get("type") != "file":
                    raise ValueError("execution workflow is not a regular file")
                actual.add(path)
        if not receipt_seen:
            raise ValueError("execution receipt workflow is missing")
        if actual != set(manifest):
            raise ValueError("execution workflow set differs from dispatch receipt")
        for path, expected in manifest.items():
            forwarded = self.execution_api.file(
                self.execution_repository, path, execution_sha
            )
            if hashlib.sha256(forwarded).hexdigest() != expected:
                raise ValueError("execution workflow differs from dispatch receipt")

    def _latest_execution_runs(self, metadata, manifest, execution_sha):
        selected = {}
        expected_ref = execution_ref(metadata)
        for run in self.execution_api.pages(
                f"/repos/{self.execution_repository}/actions/runs",
                key="workflow_runs", head_sha=execution_sha, event="push"):
            path = run.get("path")
            if (path not in manifest
                    or run.get("head_sha") != execution_sha
                    or str((run.get("head_repository") or {}).get("full_name", "")).casefold()
                    != self.execution_repository.casefold()
                    or str((run.get("repository") or {}).get("full_name", "")).casefold()
                    != self.execution_repository.casefold()
                    or run.get("event") != "push"
                    or run.get("head_branch") != expected_ref
                    or type(run.get("id")) is not int
                    or type(run.get("run_attempt", 1)) is not int):
                continue
            previous = selected.get(path)
            generation = (run["id"], run.get("run_attempt", 1))
            if previous is None or generation > (
                    previous["id"], previous.get("run_attempt", 1)):
                selected[path] = run
        return selected

    def _newer_dispatch(self, metadata):
        source = metadata["source"]
        current = (source["run_id"], source["run_attempt"])
        for run in self.source_api.pages(
                f'/repos/{source["repository"]}/actions/runs',
                key="workflow_runs", head_sha=source["sha"]):
            attempt = run.get("run_attempt", 1)
            generation = (run.get("id"), attempt)
            if (type(generation[0]) is not int or type(attempt) is not int
                    or generation <= current
                    or run.get("head_sha") != source["sha"]
                    or run.get("path") != source["workflow"]
                    or run.get("event") not in ("push", "workflow_dispatch")
                    or (run.get("repository") or {}).get("id") != source["repository_id"]
                    or (run.get("head_repository") or {}).get("id") != source["repository_id"]):
                continue
            if self._artifact(metadata, run["id"], attempt) is not None:
                return generation
        return None

    def _guard_current(self, metadata):
        self._verify_source_run(metadata)
        newer = self._newer_dispatch(metadata)
        if newer is not None:
            raise Superseded(
                f"newer source dispatch {newer[0]}, attempt {newer[1]} is available"
            )

    def _write(self, metadata, path, run, state):
        source = metadata["source"]
        self._guard_current(metadata)
        context = workflow_context(path)
        current_generation = (source["run_id"], source["run_attempt"])
        previous = latest_status(
            self.source_api, source["repository"], source["sha"], context
        )
        previous_generation = _generation((previous or {}).get("description"))
        if previous_generation is not None and previous_generation > current_generation:
            raise Superseded("a newer source generation already owns this status")
        conclusion = run.get("conclusion")
        description = _status_description(source, state, conclusion)
        url = f'{self.server_url}/{self.execution_repository}/actions/runs/{run["id"]}'
        body = {"state": state, "description": description, "target_url": url}
        posted = previous is None or any(previous.get(key) != value for key, value in body.items())
        if posted:
            post_status(
                self.source_api, source["repository"], source["sha"],
                context, state, description, url,
            )
        return {
            "path": path, "context": context, "state": state,
            "conclusion": conclusion, "run_id": run["id"],
            "run_attempt": run.get("run_attempt", 1), "url": url, "posted": posted,
        }

    def report(self, execution_sha):
        metadata = self.metadata(execution_sha)
        if metadata is None:
            return {"execution_sha": execution_sha, "skipped": "legacy batch has no source metadata"}
        if metadata["policy"] is not None:
            return {"execution_sha": execution_sha, "skipped": "explicit policy is handled by the v1 reporter"}
        source = metadata["source"]
        owner = source["repository"].split("/", 1)[0]
        if owner.casefold() not in self.owners:
            return {"execution_sha": execution_sha, "skipped": "source owner is not allowlisted"}

        self._verify_repository(metadata)
        try:
            self._verify_source_run(metadata)
        except Superseded as error:
            return {"execution_sha": execution_sha, "skipped": str(error)}
        artifact = self._artifact(metadata)
        if artifact is None:
            return {
                "execution_sha": execution_sha,
                "source_sha": source["sha"],
                "skipped": "dispatch receipt artifact is not available yet",
            }
        try:
            archive = self.artifact_downloader(
                self.source_api, source["repository"], artifact["id"]
            )
        except GitHubError as error:
            if error.status == 404:
                return {
                    "execution_sha": execution_sha,
                    "source_sha": source["sha"],
                    "skipped": "dispatch receipt artifact is not available yet",
                }
            raise
        receipt = read_receipt(archive)
        manifest = validate_receipt(receipt, metadata, execution_sha)
        self._verify_workflow_manifest(manifest, execution_sha)
        selected = self._latest_execution_runs(metadata, manifest, execution_sha)

        results = []
        for path in sorted(manifest):
            run = selected.get(path)
            if run is None:
                results.append({
                    "path": path, "context": workflow_context(path),
                    "status": "not_started", "posted": False,
                })
                continue
            state = (
                "pending" if run.get("status") != "completed"
                else "success" if run.get("conclusion") == "success"
                else "failure"
            )
            try:
                results.append(self._write(metadata, path, run, state))
            except Superseded as error:
                results.append({
                    "path": path, "context": workflow_context(path),
                    "skipped": str(error), "posted": False,
                })

        return {
            "execution_sha": execution_sha,
            "source_repository": source["repository"],
            "source_sha": source["sha"],
            "source_run_id": source["run_id"],
            "source_run_attempt": source["run_attempt"],
            "workflows": results,
        }
