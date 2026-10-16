"""Validate receiver policy from the execution repository's default branch."""

import re

from source_metadata import POLICY, REPOSITORY
from source_yaml import loads as load_checks_yaml

WORKFLOW = re.compile(r"^[A-Za-z0-9_-]+\.ya?ml$")


def checks_policy(checks):
    if (not isinstance(checks, dict) or type(checks.get("version")) is not int
            or checks["version"] != 1):
        raise ValueError("checks.version must be 1")
    # Keep the wire identifier stable for in-flight batches and old callers.
    return "checks-v1"


def requested_checks(raw="", legacy=""):
    if not raw:
        return legacy
    checks = load_checks_yaml(raw.rstrip() + "\n")
    if not isinstance(checks, dict) or set(checks) != {"version"}:
        raise ValueError("source checks requires only version")
    policy = checks_policy(checks)
    if legacy and legacy != policy:
        raise ValueError("checks conflicts with the legacy status policy")
    return policy


def load_policy(config, source_key, execution_repository):
    if config.get("schema_version") != 1 or config.get("execution_repository") != execution_repository:
        raise ValueError("invalid trusted status configuration")
    source = dict(config["sources"][source_key])
    if "checks" in source:
        if "policies" in source:
            raise ValueError("checks and legacy policies cannot be combined")
        checks = source["checks"]
        policy_id = checks_policy(checks)
        if set(checks) - {"version", "workflows", "missing_after_seconds"}:
            raise ValueError("unknown checks fields")
        source["policies"] = {policy_id: {key: value for key, value in checks.items()
                                       if key != "version"}}
    if not REPOSITORY.fullmatch(source["repository"]):
        raise ValueError("invalid trusted source repository")
    if type(source["repository_id"]) is not int or source["repository_id"] <= 0:
        raise ValueError("trusted source repository ID is required")
    expected_dispatch = source["repository"].split("/", 1)[1] + "/dynamic-dispatch"
    if source.get("dispatch_context") != expected_dispatch:
        raise ValueError("dispatch context does not match the source protocol")
    context = source.get("status_context", "")
    if context != source["repository"].split("/", 1)[1] + "/dynamic-checks":
        raise ValueError("invalid trusted result context")
    if not source.get("trigger_workflows") or any(
        not path.startswith(".github/workflows/") or not WORKFLOW.fullmatch(path.rsplit("/", 1)[1])
        for path in source["trigger_workflows"]
    ):
        raise ValueError("trusted trigger workflow paths are required")
    policies = source.get("policies", {})
    if not policies:
        raise ValueError("at least one versioned policy is required")
    for policy_id, policy in policies.items():
        if not POLICY.fullmatch(policy_id):
            raise ValueError("invalid trusted policy ID")
        workflows = policy.get("workflows")
        if not isinstance(workflows, list) or not workflows:
            raise ValueError("required workflow list cannot be empty")
        paths = [entry.get("path", "") for entry in workflows]
        if len(paths) != len(set(paths)) or any(not WORKFLOW.fullmatch(path) for path in paths):
            raise ValueError("invalid or duplicate required workflow")
        if "dyn-receipt.yml" in paths:
            raise ValueError("receipt cannot stand in for required checks")
        if any(not isinstance(entry.get("name"), str) or not entry["name"] for entry in workflows):
            raise ValueError("required workflow names are required")
        timeout = policy.get("missing_after_seconds", 600)
        if type(timeout) is not int or not 60 <= timeout <= 3600:
            raise ValueError("invalid missing-workflow grace period")
    return source
