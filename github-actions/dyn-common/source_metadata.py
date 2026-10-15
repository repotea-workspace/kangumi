"""Versioned identity shared by forwarding, immutable checkout and reporting."""

import json
import re
from pathlib import Path

SCHEMA_VERSION = 1
SHA = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
POLICY = re.compile(r"^[a-z][a-z0-9-]{0,63}$")


def validate_metadata(value, expected_repository=None, expected_execution=None):
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported dynamic source metadata")
    source = value.get("source")
    if not isinstance(source, dict):
        raise ValueError("missing dynamic source identity")
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
        if not isinstance(source.get(key), str) or not source[key] or "\n" in source[key] or "\r" in source[key]:
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
    return value


def build_metadata(env, event, owner, policy):
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
    return validate_metadata({
        "schema_version": SCHEMA_VERSION,
        "source": source,
        "execution_repository": owner + "/dynamic-actions",
        "policy": policy or None,
    })


def metadata_directory(workspace):
    workspace = Path(workspace)
    restored = workspace / "__origin__" / ".github"
    return restored if restored.is_dir() else workspace / ".github"


def read_metadata(directory, expected_repository=None):
    path = Path(directory) / "source.json"
    if not path.exists():
        return None
    # Invalid new metadata must never silently fall back to a mutable branch.
    return validate_metadata(json.loads(path.read_text()), expected_repository)


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
    ref = Path(ref_file).read_text().strip()
    if not ref or "\n" in ref or "\r" in ref:
        raise ValueError("invalid legacy ref")
    return ref


def write_outputs(path, values):
    with open(path, "a", encoding="utf-8") as stream:
        for key, value in values.items():
            text = str(value)
            if "\n" in text or "\r" in text:
                raise ValueError(f"invalid output {key}")
            stream.write(f"{key}={text}\n")
