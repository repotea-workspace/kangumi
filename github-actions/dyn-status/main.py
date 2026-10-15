#!/usr/bin/env python3
"""Wire the trusted receiver; never check out or execute forwarded source."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dyn-common"))
from github_api import GitHub
from reconciliation import candidates
from status_policy import load_policy
from status_report import StatusReporter


def main():
    env = os.environ
    config = json.loads(Path(env["STATUS_CONFIG"]).read_text())
    policy = load_policy(config, env["SOURCE_KEY"], env["GITHUB_REPOSITORY"])
    execution = GitHub(env["EXECUTION_READ_TOKEN"], env["GITHUB_API_URL"])
    source = GitHub(env["SOURCE_STATUS_TOKEN"], env["GITHUB_API_URL"])
    event = json.loads(Path(env["GITHUB_EVENT_PATH"]).read_text())
    summary_url = f'{env["GITHUB_SERVER_URL"]}/{env["GITHUB_REPOSITORY"]}/actions/runs/{env["GITHUB_RUN_ID"]}'
    reporter = StatusReporter(execution, source, env["GITHUB_REPOSITORY"], policy,
                              env["GITHUB_SERVER_URL"], summary_url=summary_url)
    failures = []
    for sha in candidates(execution, env["GITHUB_REPOSITORY"], event, env["GITHUB_EVENT_NAME"]):
        try:
            result = reporter.report(sha)
            print(json.dumps(result))
            with open(env["GITHUB_STEP_SUMMARY"], "a") as stream:
                if "state" in result:
                    stream.write(f'- {result["source_sha"]}: **{result["state"]}** — [details]({result["url"]})\n')
                    for url in result["runs"]:
                        stream.write(f'  - [Execution run]({url})\n')
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
