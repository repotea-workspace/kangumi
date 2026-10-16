"""Versioned identity shared by forwarding, immutable checkout and reporting."""

from datetime import datetime, timezone
from fnmatch import fnmatchcase
import json
import re
import uuid
from pathlib import Path

from source_yaml import dumps as dump_source_yaml
from source_yaml import loads as load_source_yaml


SCHEMA_VERSION = 2
LEGACY_SCHEMA_VERSION = 1
LEGACY_FORMAT = "legacy"
SOURCE_YAML_FORMAT = "source-yml"
SHA = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
POLICY = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
SOURCE_KEYS = {
    "repository", "repository_id", "sha", "ref_type", "ref_name",
    "run_id", "run_attempt", "workflow",
}
PATTERN = re.compile(r"^[!-Z\\^-~]+$")


def _object_without_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _valid_text(value, *, empty=False, limit=65536):
    return (
        isinstance(value, str)
        and (empty or bool(value))
        and len(value.encode("utf-8")) <= limit
        and "\x00" not in value
    )


def validate_metadata(value, expected_repository=None, expected_execution=None):
    if (not isinstance(value, dict)
            or type(value.get("schema_version")) is not int
            or value["schema_version"] not in (
                LEGACY_SCHEMA_VERSION, SCHEMA_VERSION)):
        raise ValueError("unsupported dynamic source metadata")
    version = value["schema_version"]
    expected_keys = {"schema_version", "source", "execution_repository", "policy"}
    if version == SCHEMA_VERSION:
        expected_keys.update(("commit", "dispatch"))
    if set(value) != expected_keys:
        raise ValueError("invalid dynamic source metadata fields")

    source = value.get("source")
    if not isinstance(source, dict) or set(source) != SOURCE_KEYS:
        raise ValueError("missing or invalid dynamic source identity")
    if not REPOSITORY.fullmatch(str(source.get("repository", ""))):
        raise ValueError("invalid source repository")
    if expected_repository and source["repository"] != expected_repository:
        raise ValueError("source repository does not match the caller")
    if not SHA.fullmatch(str(source.get("sha", ""))):
        raise ValueError("source SHA must be a full immutable commit")
    for key in ("repository_id", "run_id", "run_attempt"):
        if type(source.get(key)) is not int or source[key] <= 0:
            raise ValueError(f"invalid source {key}")
    if source.get("ref_type") not in ("branch", "tag"):
        raise ValueError("invalid source ref type")
    for key in ("ref_name", "workflow"):
        if not _valid_text(source.get(key), limit=4096) or "\n" in source[key] or "\r" in source[key]:
            raise ValueError(f"invalid source {key}")
    if not source["workflow"].startswith(".github/workflows/"):
        raise ValueError("invalid source workflow path")

    execution = value.get("execution_repository")
    if not isinstance(execution, str) or not REPOSITORY.fullmatch(execution):
        raise ValueError("invalid execution repository")
    if expected_execution and execution != expected_execution:
        raise ValueError("execution repository does not match the receiver")
    policy = value.get("policy")
    if policy is not None and (not isinstance(policy, str) or not POLICY.fullmatch(policy)):
        raise ValueError("invalid status policy")

    if version == SCHEMA_VERSION:
        commit = value.get("commit")
        if not isinstance(commit, dict) or set(commit) != {"message", "authors"}:
            raise ValueError("invalid source commit metadata")
        if not _valid_text(commit.get("message"), limit=65536):
            raise ValueError("invalid source commit message")
        authors = commit.get("authors")
        if not isinstance(authors, list) or not authors or len(authors) > 100:
            raise ValueError("invalid source commit authors")
        if any(not _valid_text(author, limit=100) or "\n" in author or "\r" in author
               for author in authors):
            raise ValueError("invalid source commit author")

        dispatch = value.get("dispatch")
        if not isinstance(dispatch, dict) or set(dispatch) != {"created_at"}:
            raise ValueError("invalid dispatch metadata")
        created_at = dispatch.get("created_at")
        if not _valid_text(created_at, limit=64):
            raise ValueError("invalid dispatch time")
        try:
            parsed = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("invalid dispatch time") from error
        if parsed.tzinfo is None:
            raise ValueError("dispatch time must include a timezone")
    return value


def _commit_details(env, event):
    head = event.get("head_commit") or {}
    message = head.get("message") or "Dynamic workflow dispatch"
    authors = sorted({
        commit.get("author", {}).get("username")
        for commit in event.get("commits", [])
        if commit.get("author", {}).get("username")
    })
    if not authors:
        authors = [head.get("author", {}).get("username") or env["GITHUB_ACTOR"]]
    return {"message": message, "authors": authors}


def build_metadata(env, event, owner, policy, schema_version=LEGACY_SCHEMA_VERSION,
                   dispatched_at=None):
    repository = env["GITHUB_REPOSITORY"]
    workflow_ref = env["GITHUB_WORKFLOW_REF"]
    prefix = repository + "/"
    if not workflow_ref.startswith(prefix):
        raise ValueError("workflow repository does not match source")
    source = {
        "repository": repository,
        "repository_id": int(env["GITHUB_REPOSITORY_ID"]),
        "sha": env["GITHUB_SHA"],
        "ref_type": env["GITHUB_REF_TYPE"],
        "ref_name": env["GITHUB_REF_NAME"],
        "run_id": int(env["GITHUB_RUN_ID"]),
        "run_attempt": int(env["GITHUB_RUN_ATTEMPT"]),
        "workflow": workflow_ref[len(prefix):].split("@", 1)[0],
    }
    if event.get("repository", {}).get("id") != source["repository_id"]:
        raise ValueError("event repository does not match source")
    metadata = {
        "schema_version": schema_version,
        "source": source,
        "execution_repository": owner + "/dynamic-actions",
        "policy": policy or None,
    }
    if schema_version == SCHEMA_VERSION:
        metadata["commit"] = _commit_details(env, event)
        metadata["dispatch"] = {
            "created_at": dispatched_at or datetime.now(timezone.utc).isoformat(
                timespec="seconds").replace("+00:00", "Z")
        }
    return validate_metadata(metadata)


def write_metadata(directory, metadata, metadata_format):
    directory = Path(directory)
    if metadata_format == LEGACY_FORMAT:
        if metadata["schema_version"] != LEGACY_SCHEMA_VERSION:
            raise ValueError("legacy format requires schema version 1")
        (directory / "source.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    elif metadata_format == SOURCE_YAML_FORMAT:
        if metadata["schema_version"] != SCHEMA_VERSION:
            raise ValueError("source-yml format requires schema version 2")
        (directory / "source.yml").write_text(
            dump_source_yaml(metadata), encoding="utf-8")
    else:
        raise ValueError("metadata-format must be legacy or source-yml")


def load_metadata(raw, filename):
    if filename == "source.yml":
        value = load_source_yaml(raw)
        if (not isinstance(value, dict)
                or type(value.get("schema_version")) is not int
                or value["schema_version"] != SCHEMA_VERSION):
            raise ValueError("source.yml requires schema version 2")
    elif filename == "source.json":
        try:
            value = json.loads(raw, object_pairs_hook=_object_without_duplicates)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("invalid dynamic source JSON") from error
        if (not isinstance(value, dict)
                or type(value.get("schema_version")) is not int
                or value["schema_version"] != LEGACY_SCHEMA_VERSION):
            raise ValueError("source.json requires schema version 1")
    else:
        raise ValueError("unsupported dynamic source metadata file")
    return validate_metadata(value)


def metadata_directory(workspace):
    workspace = Path(workspace)
    restored = workspace / "__origin__" / ".github"
    return restored if restored.is_dir() else workspace / ".github"


def read_metadata(directory, expected_repository=None, expected_execution=None):
    directory = Path(directory)
    for filename in ("source.yml", "source.json"):
        path = directory / filename
        if path.exists():
            metadata = load_metadata(path.read_bytes(), filename)
            return validate_metadata(metadata, expected_repository, expected_execution)
    return None


def read_remote_metadata(api, repository, ref, expected_repository=None,
                         expected_execution=None):
    from github_api import GitHubError
    for filename in ("source.yml", "source.json"):
        path = ".github/" + filename
        try:
            raw = api.file(repository, path, ref)
        except GitHubError as error:
            if error.status == 404:
                continue
            raise
        metadata = load_metadata(raw, filename)
        return validate_metadata(metadata, expected_repository, expected_execution)
    return None


def checkout_ref(workspace, repository, explicit_ref="", ref_file=""):
    metadata = read_metadata(metadata_directory(workspace))
    if metadata and metadata["source"]["repository"] != repository:
        if metadata["policy"]:
            raise ValueError("source repository does not match the caller")
        # Existing callers may use clone-dyn for an explicitly selected
        # auxiliary repository; automatic metadata must not change that ref.
        metadata = None
    if explicit_ref:
        if metadata and metadata["policy"] and explicit_ref != metadata["source"]["sha"]:
            raise ValueError("explicit ref differs from immutable dynamic source SHA")
        return explicit_ref
    if metadata:
        return metadata["source"]["sha"]
    if not ref_file:
        raise ValueError("legacy checkout requires ref or ref_file")
    ref = Path(ref_file).read_text(encoding="utf-8").strip()
    if not ref or "\n" in ref or "\r" in ref:
        raise ValueError("invalid legacy ref")
    return ref


def parse_patterns(value, label):
    if not isinstance(value, str):
        raise ValueError(f"{label} patterns must be text")
    patterns = []
    for line in value.splitlines():
        if not line:
            continue
        if line != line.strip() or len(line) > 255 or not PATTERN.fullmatch(line):
            raise ValueError(f"invalid {label} pattern: {line!r}")
        if "[" in line or "]" in line:
            raise ValueError(f"{label} patterns support only exact names, * and ?")
        patterns.append(line)
    if len(patterns) > 100:
        raise ValueError(f"too many {label} patterns")
    return patterns


def matches_ref(ref_type, ref_name, branches="", tags=""):
    branch_patterns = parse_patterns(branches, "branch")
    tag_patterns = parse_patterns(tags, "tag")
    if not branch_patterns and not tag_patterns:
        return True
    patterns = branch_patterns if ref_type == "branch" else tag_patterns
    return any(fnmatchcase(ref_name, pattern) for pattern in patterns)


def write_outputs(path, values):
    with open(path, "a", encoding="utf-8") as stream:
        for key, value in values.items():
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", key):
                raise ValueError("invalid output name")
            text = str(value)
            if "\n" not in text and "\r" not in text:
                stream.write(f"{key}={text}\n")
                continue
            delimiter = "dyn_" + uuid.uuid4().hex
            while delimiter in text:
                delimiter = "dyn_" + uuid.uuid4().hex
            stream.write(f"{key}<<{delimiter}\n{text}\n{delimiter}\n")
