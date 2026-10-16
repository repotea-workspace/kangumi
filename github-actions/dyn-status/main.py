#!/usr/bin/env python3
"""Route and report trusted, on-demand dynamic CI events."""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dyn-common"))
from github_api import GitHub
from reconciliation import EventExecution, candidates
from receiver import report_group, group_owners, route_group
from source_metadata import write_outputs
from status_config import load_config
from status_policy import load_policy
from status_report import StatusReporter


RECEIPT_WAIT_SECONDS = 120
POLICY_WAIT_SECONDS = 3720
RUN_DISCOVERY_SECONDS = 30


def reconcile(report, sleep=time.sleep, clock=time.monotonic):
    """Finish event-local consistency work; there is no periodic repair job."""
    started = clock()
    while True:
        result = report()
        missing_receipt = (
            result.get("skipped") == "dispatch receipt artifact is not available yet"
            or result.get("retry_reason") == "dispatch_receipt"
        )
        # Missing automatic workflows can legitimately be path-filtered.
        # Allow bounded list propagation, then preserve not_started semantics.
        if (any(item.get("status") == "not_started" for item in result.get("workflows", []))
                and not any(item.get("state") == "pending" for item in result.get("workflows", []))):
            remaining = started + RUN_DISCOVERY_SECONDS - clock()
            if remaining > 0:
                sleep(min(10, remaining))
                continue
        delay = result.get("retry_after_seconds", 0)
        if not missing_receipt and not delay:
            return result
        limit = RECEIPT_WAIT_SECONDS if missing_receipt else POLICY_WAIT_SECONDS
        remaining = started + limit - clock()
        if remaining <= 0:
            raise TimeoutError("dynamic evidence is not ready; rerun this receiver or reconcile its SHA manually")
        sleep(min(10 if missing_receipt else max(1, delay), 60, remaining))


def main():
    env = os.environ
    config = load_config(env["STATUS_CONFIG"])
    mode = env.get("STATUS_MODE", "report") or "report"
    if mode not in ("route", "report"):
        raise ValueError("mode must be route or report")
    execution = GitHub(env["EXECUTION_READ_TOKEN"], env["GITHUB_API_URL"])
    event = json.loads(Path(env["GITHUB_EVENT_PATH"]).read_text())
    if mode == "route" and (
            env["GITHUB_EVENT_NAME"] not in ("workflow_run", "workflow_dispatch")
            or (env["GITHUB_EVENT_NAME"] == "workflow_dispatch"
                and not event.get("inputs", {}).get("execution_sha"))):
        raise ValueError("route requires one workflow event or an explicit execution SHA")
    shas = candidates(execution, env["GITHUB_REPOSITORY"], event, env["GITHUB_EVENT_NAME"],
                      lookback_hours=48)
    if mode == "route":
        if len(shas) != 1:
            raise ValueError("route requires exactly one execution SHA")
        result = route_group(execution, env["GITHUB_REPOSITORY"], config, shas[0])
        write_outputs(env["GITHUB_OUTPUT"], result)
        print(json.dumps(result))
        return

    group = env.get("CREDENTIAL_GROUP", "")
    if group:
        group_owners(config, group, env["GITHUB_REPOSITORY"])
        policy = None
    else:
        policy = load_policy(config, env["SOURCE_KEY"], env["GITHUB_REPOSITORY"])
    source = GitHub(env["SOURCE_STATUS_TOKEN"], env["GITHUB_API_URL"])
    if env["GITHUB_EVENT_NAME"] == "workflow_run":
        execution = EventExecution(execution, env["GITHUB_REPOSITORY"], event["workflow_run"])
    summary_url = f'{env["GITHUB_SERVER_URL"]}/{env["GITHUB_REPOSITORY"]}/actions/runs/{env["GITHUB_RUN_ID"]}'
    failures = []
    for sha in shas:
        try:
            def report():
                if isinstance(execution, EventExecution):
                    execution.refresh()
                if group:
                    return report_group(execution, source, env["GITHUB_REPOSITORY"], config,
                                        group, sha, env["GITHUB_SERVER_URL"], summary_url)
                return StatusReporter(execution, source, env["GITHUB_REPOSITORY"], policy,
                                      env["GITHUB_SERVER_URL"], summary_url=summary_url).report(sha)

            result = reconcile(report)
            print(json.dumps(result))
            with open(env["GITHUB_STEP_SUMMARY"], "a") as stream:
                if "skipped" in result:
                    stream.write(f'- {sha}: **skipped** — {result["skipped"]}\n')
                if "state" in result:
                    stream.write(f'- {result["source_sha"]}: **{result["state"]}** — [details]({result["url"]})\n')
                    for url in result["runs"]:
                        stream.write(f'  - [Execution run]({url})\n')
                for workflow in result.get("workflows", []):
                    if "url" in workflow:
                        stream.write(f'- {result["source_sha"]}: **{workflow["state"]}** — [execution run]({workflow["url"]})\n')
        except Exception as error:
            print(json.dumps({"error": "Cannot reconcile", "execution_sha": sha,
                              "type": type(error).__name__, "message": str(error)}))
            failures.append(sha)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
