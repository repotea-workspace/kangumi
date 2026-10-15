#!/usr/bin/env python3
"""Wire the trusted receiver; never check out or execute forwarded source."""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dyn-common"))
from github_api import GitHub
from reconciliation import candidates
from receiver import report_group, group_owners
from status_policy import load_policy
from status_report import StatusReporter


def main():
    env = os.environ
    config = json.loads(Path(env["STATUS_CONFIG"]).read_text())
    group = env.get("CREDENTIAL_GROUP", "")
    if group:
        group_owners(config, group, env["GITHUB_REPOSITORY"])
        policy = None
    else:
        policy = load_policy(config, env["SOURCE_KEY"], env["GITHUB_REPOSITORY"])
    execution = GitHub(env["EXECUTION_READ_TOKEN"], env["GITHUB_API_URL"])
    source = GitHub(env["SOURCE_STATUS_TOKEN"], env["GITHUB_API_URL"])
    event = json.loads(Path(env["GITHUB_EVENT_PATH"]).read_text())
    summary_url = f'{env["GITHUB_SERVER_URL"]}/{env["GITHUB_REPOSITORY"]}/actions/runs/{env["GITHUB_RUN_ID"]}'
    reporter = StatusReporter(execution, source, env["GITHUB_REPOSITORY"], policy,
                              env["GITHUB_SERVER_URL"], summary_url=summary_url) if policy else None
    failures = []
    for sha in candidates(execution, env["GITHUB_REPOSITORY"], event, env["GITHUB_EVENT_NAME"],
                          lookback_hours=48):
        try:
            for attempt in range(3):
                result = (report_group(execution, source, env["GITHUB_REPOSITORY"], config, group, sha,
                                       env["GITHUB_SERVER_URL"], summary_url)
                          if group else reporter.report(sha))
                if (env["GITHUB_EVENT_NAME"] != "workflow_run" or attempt == 2
                        or result.get("skipped") != "dispatch receipt artifact is not available yet"):
                    break
                time.sleep(3)
            print(json.dumps(result))
            with open(env["GITHUB_STEP_SUMMARY"], "a") as stream:
                if "state" in result:
                    stream.write(f'- {result["source_sha"]}: **{result["state"]}** — [details]({result["url"]})\n')
                    for url in result["runs"]:
                        stream.write(f'  - [Execution run]({url})\n')
                for workflow in result.get("workflows", []):
                    if "url" in workflow:
                        stream.write(f'- {result["source_sha"]}: **{workflow["state"]}** — [execution run]({workflow["url"]})\n')
        except Exception as error:
            # An unrelated bad batch must not prevent other pending batches
            # from being reconciled. Still fail the receiver visibly.
            print(json.dumps({"error": "Cannot reconcile", "execution_sha": sha,
                              "type": type(error).__name__, "message": str(error)}))
            failures.append(sha)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
