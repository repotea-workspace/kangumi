"""Route immutable batches using centrally configured credential owner groups."""

from auto_report import AutoStatusReporter
from source_metadata import read_remote_metadata
from status_config import validate_config
from status_policy import load_policy
from status_report import StatusReporter


def group_owners(config, key, execution_repository):
    validate_config(config, execution_repository)
    if key not in config["credential_groups"]:
        raise ValueError("unknown credential group")
    return [owner.lower() for owner in config["credential_groups"][key]["owners"]]


def route_group(execution, repository, config, sha):
    validate_config(config, repository, require_secrets=True)
    metadata = read_remote_metadata(execution, repository, sha, expected_execution=repository)
    if metadata is None:
        return {"matched": "false", "reason": "legacy batch"}
    owner = metadata["source"]["repository"].split("/", 1)[0].lower()
    for key, group in config["credential_groups"].items():
        if owner in [value.lower() for value in group["owners"]]:
            return {
                "matched": "true", "group": key,
                "secret_name": group["secret_name"], "execution_sha": sha,
            }
    return {"matched": "false", "reason": "source owner is not allowlisted"}


def report_group(execution, source, repository, config, group, sha, server_url, summary_url):
    owners = group_owners(config, group, repository)
    metadata = read_remote_metadata(
        execution, repository, sha, expected_execution=repository
    )
    if metadata is None:
        return {"execution_sha": sha, "skipped": "legacy batch"}
    origin = metadata["source"]["repository"]
    if origin.split("/", 1)[0].lower() not in owners:
        return {"execution_sha": sha, "skipped": "another credential group"}
    if metadata["policy"]:
        matching = [key for key, policy in config.get("sources", {}).items() if policy["repository"] == origin]
        if not matching:
            # A completion can arrive after its source opts out of aggregate
            # reporting. Do not turn that retired batch into automatic checks.
            return {"execution_sha": sha,
                    "skipped": "explicit aggregate source is not registered"}
        if len(matching) != 1:
            raise ValueError("explicit aggregate source registration is ambiguous")
        policy = load_policy(config, matching[0], repository)
        return StatusReporter(execution, source, repository, policy, server_url, summary_url=summary_url).report(sha)
    return AutoStatusReporter(execution, source, repository, owners, server_url=server_url).report(sha)
