"""Route immutable batches using centrally configured credential owner groups."""

from auto_report import AutoStatusReporter
from source_metadata import read_remote_metadata
from status_policy import load_policy
from status_report import StatusReporter


def group_owners(config, key, execution_repository):
    if config.get("schema_version") != 1 or config.get("execution_repository") != execution_repository:
        raise ValueError("invalid trusted status configuration")
    owners = config.get("credential_groups", {}).get(key, {}).get("owners")
    if not isinstance(owners, list) or not owners or any(
        not isinstance(owner, str) or not owner or not all(c.isascii() and (c.isalnum() or c == "-") for c in owner)
        for owner in owners
    ):
        raise ValueError("credential group requires valid source owners")
    normalized = [owner.lower() for owner in owners]
    if len(set(normalized)) != len(normalized):
        raise ValueError("duplicate credential owner")
    all_owners = [owner.lower() for group in config["credential_groups"].values() for owner in group["owners"]]
    if len(set(all_owners)) != len(all_owners):
        raise ValueError("source owner belongs to multiple credential groups")
    return normalized


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
        if len(matching) != 1:
            raise ValueError("explicit aggregate policy requires a registered source")
        policy = load_policy(config, matching[0], repository)
        return StatusReporter(execution, source, repository, policy, server_url, summary_url=summary_url).report(sha)
    return AutoStatusReporter(execution, source, repository, owners, server_url=server_url).report(sha)
