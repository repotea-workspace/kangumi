"""Source-owned forwarding receipts and failed-trigger finalization."""

import re
from pathlib import Path

from github_api import is_source_bot, latest_status, post_status
from source_metadata import (LEGACY_FORMAT, LEGACY_SCHEMA_VERSION, SCHEMA_VERSION,
                             SHA, build_metadata, write_metadata)


AUTO_CONTEXT_PREFIX = "dynamic / "
AUTO_GENERATION = re.compile(r"^Source run (\d+), attempt (\d+):")


def dispatch_context(repository):
    return repository.split("/", 1)[1] + "/dynamic-dispatch"


def generation_description(run_id, attempt):
    return f"Dynamic dispatch: source run {run_id}, attempt {attempt}"


def source_run_url(server, repository, run_id):
    return f"{server}/{repository}/actions/runs/{run_id}"


def automatic_description(source, result):
    return f'Source run {source["run_id"]}, attempt {source["run_attempt"]}: {result}'


def latest_automatic_statuses(api, repository, sha):
    """Return the latest status for each context owned by automatic reporting."""
    statuses = []
    seen = set()
    for status in api.statuses(repository, sha):
        context = status.get("context")
        if not isinstance(context, str) or context in seen:
            continue
        seen.add(context)
        match = AUTO_GENERATION.match(status.get("description", ""))
        if context.startswith(AUTO_CONTEXT_PREFIX) and match:
            statuses.append((status, tuple(map(int, match.groups()))))
    return statuses


def _prepare_automatic_statuses(api, env, source, prior):
    url = source_run_url(
        env["GITHUB_SERVER_URL"], source["repository"], source["run_id"]
    )
    description = automatic_description(source, "queued or running")
    current_generation = (source["run_id"], source["run_attempt"])
    for status, generation in prior:
        # Only a rerun of the same source workflow run is known to have the
        # same ref and event selection. A different source run may target the
        # same SHA through a tag or another Trigger whose workflows are filtered.
        if generation[0] == current_generation[0] and generation[1] < current_generation[1]:
            post_status(api, source["repository"], source["sha"],
                        status["context"], "pending", description, url)


def prepare_dispatch(api, env, event, owner, policy, metadata_dir, sentinel_path,
                     metadata_format=LEGACY_FORMAT):
    schema_version = (
        LEGACY_SCHEMA_VERSION if metadata_format == LEGACY_FORMAT else SCHEMA_VERSION
    )
    metadata = build_metadata(env, event, owner, policy, schema_version=schema_version)
    directory = Path(metadata_dir)
    directory.mkdir(parents=True, exist_ok=True)
    write_metadata(directory, metadata, metadata_format)
    source = metadata["source"]
    if not policy:
        inject_receipt(directory, sentinel_path)
        if api is None:
            return metadata
    context = dispatch_context(source["repository"])
    current = latest_status(api, source["repository"], source["sha"], context)
    if current and is_source_bot(current):
        match = re.fullmatch(r"Dynamic dispatch: source run (\d+), attempt (\d+)", current.get("description", ""))
        if match and tuple(map(int, match.groups())) > (source["run_id"], source["run_attempt"]):
            raise ValueError("a newer source run already owns this SHA")
    prior = []
    if not policy:
        prior = latest_automatic_statuses(
            api, source["repository"], source["sha"]
        )
        generation = (source["run_id"], source["run_attempt"])
        if any(item_generation > generation for _, item_generation in prior):
            raise ValueError("a newer source run already owns an automatic status")
    else:
        post_status(api, source["repository"], source["sha"],
                    source["repository"].split("/", 1)[1] + "/dynamic-checks",
                    "pending", "Waiting for dynamic execution",
                    source_run_url(env["GITHUB_SERVER_URL"], source["repository"], source["run_id"]))
    status = post_status(
        api, source["repository"], source["sha"], dispatch_context(source["repository"]),
        "pending", generation_description(source["run_id"], source["run_attempt"]),
        source_run_url(env["GITHUB_SERVER_URL"], source["repository"], source["run_id"]),
    )
    if not is_source_bot(status):
        raise ValueError("status_token must be the source repository GITHUB_TOKEN")
    if not policy:
        _prepare_automatic_statuses(api, env, source, prior)
    else:
        inject_receipt(directory, sentinel_path)
    return metadata


def inject_receipt(directory, sentinel_path):
    target = directory / "workflows" / "dyn-receipt.yml"
    if target.exists():
        raise ValueError("dyn-receipt.yml is reserved by the forwarding protocol")
    target.write_bytes(Path(sentinel_path).read_bytes())


def finish_dispatch(api, env, metadata, execution_sha=None):
    if api is None:
        return
    source = metadata["source"]
    context = dispatch_context(source["repository"])
    expected_description = generation_description(source["run_id"], source["run_attempt"])
    current = latest_status(api, source["repository"], source["sha"], context)
    expected_url = source_run_url(env["GITHUB_SERVER_URL"], source["repository"], source["run_id"])
    if not current or not is_source_bot(current) or current["description"] != expected_description:
        return  # A newer source run owns this SHA now.
    if execution_sha:
        if current["state"] != "pending" or current["target_url"] != expected_url:
            return
        if not SHA.fullmatch(execution_sha):
            raise ValueError("execution SHA must be immutable")
        url = f'{env["GITHUB_SERVER_URL"]}/{metadata["execution_repository"]}/commit/{execution_sha}'
        state = "success"
        description = expected_description
    else:
        forwarded_prefix = (
            f'{env["GITHUB_SERVER_URL"]}/{metadata["execution_repository"]}/commit/'
        )
        target = current.get("target_url", "")
        pending = current.get("state") == "pending" and target == expected_url
        forwarded = (
            current.get("state") == "success"
            and target.startswith(forwarded_prefix)
            and SHA.fullmatch(target[len(forwarded_prefix):])
        )
        if not pending and not forwarded:
            return
        url = expected_url
        state = "error"
        description = expected_description
    post_status(api, source["repository"], source["sha"], context, state, description, url)
    if not execution_sha and metadata["policy"]:
        post_status(api, source["repository"], source["sha"],
                    source["repository"].split("/", 1)[1] + "/dynamic-checks",
                    "error", "Dynamic forwarding did not complete", url)
    elif not execution_sha:
        generation = (source["run_id"], source["run_attempt"])
        for status, status_generation in latest_automatic_statuses(
                api, source["repository"], source["sha"]):
            if (status_generation == generation
                    and status.get("state") == "pending"
                    and status.get("target_url") == expected_url):
                post_status(
                    api, source["repository"], source["sha"], status["context"],
                    "error", automatic_description(source, "forwarding failed"), expected_url,
                )


def finalize_failed_trigger(api, env, event, trigger_path, policy="checks-v1"):
    run = event.get("workflow_run", {})
    repository = event.get("repository", {})
    if env.get("GITHUB_EVENT_NAME") != "workflow_run" or run.get("status") != "completed":
        raise ValueError("dispatch finalizer requires a completed workflow_run")
    if run.get("path") != trigger_path or run.get("conclusion") == "success":
        return
    source_repository = env["GITHUB_REPOSITORY"]
    if repository.get("full_name") != source_repository or run.get("repository", {}).get("id") != repository.get("id"):
        raise ValueError("workflow_run repository mismatch")
    sha = run.get("head_sha", "")
    if not SHA.fullmatch(sha):
        raise ValueError("invalid source SHA")
    context = dispatch_context(source_repository)
    current = latest_status(api, source_repository, sha, context)
    expected = generation_description(run["id"], run["run_attempt"])
    url = source_run_url(env["GITHUB_SERVER_URL"], source_repository, run["id"])
    if current is not None and not (
        is_source_bot(current) and current["state"] == "pending"
        and current["target_url"] == url and current["description"] == expected
    ):
        return
    post_status(api, source_repository, sha, context, "error", expected, url)
    if policy:
        post_status(api, source_repository, sha, source_repository.split("/", 1)[1] + "/dynamic-checks",
                    "error", f'Dynamic forwarding {run.get("conclusion") or "failed"}', url)
    source = {"run_id": run["id"], "run_attempt": run["run_attempt"]}
    generation = (run["id"], run["run_attempt"])
    for status, status_generation in latest_automatic_statuses(api, source_repository, sha):
        if (status_generation == generation and status.get("state") == "pending"
                and status.get("target_url") == url):
            post_status(api, source_repository, sha, status["context"], "error",
                        automatic_description(source, "forwarding failed"), url)
