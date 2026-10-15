#!/usr/bin/env python3
"""CLI wiring for source-owned forwarding receipts."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dyn-common"))
from dispatch import finish_dispatch, prepare_dispatch
from github_api import GitHub
from source_metadata import SHA, read_metadata, write_outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("prepare", "finish", "fail"))
    parser.add_argument("--metadata-dir", default=".github")
    parser.add_argument("--execution-sha")
    args = parser.parse_args()
    env = os.environ
    policy = env.get("STATUS_POLICY", "")
    api = GitHub(env.get("SOURCE_STATUS_TOKEN", ""), env["GITHUB_API_URL"]) if policy else None
    if args.operation == "prepare":
        event = json.loads(Path(env["GITHUB_EVENT_PATH"]).read_text())
        prepare_dispatch(api, env, event, env["EXECUTION_OWNER"], policy, args.metadata_dir,
                         Path(__file__).with_name("receipt.yml"))
    else:
        metadata = read_metadata(args.metadata_dir, env["GITHUB_REPOSITORY"])
        finish_dispatch(api, env, metadata, args.execution_sha if args.operation == "finish" else None)
        if args.operation == "finish" and not metadata["policy"]:
            if not SHA.fullmatch(args.execution_sha or ""):
                raise ValueError("execution SHA must be immutable")
            directory = Path(env["RUNNER_TEMP"]) / ("dyn-dispatch-" + env["GITHUB_RUN_ID"] + "-" + env["GITHUB_RUN_ATTEMPT"])
            directory.mkdir(parents=True, exist_ok=True)
            receipt = directory / "receipt.json"
            manifest = {
                ".github/workflows/" + path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted((Path(args.metadata_dir) / "workflows").iterdir())
                if path.is_file() and path.suffix in (".yml", ".yaml") and path.name != "dyn-receipt.yml"
            }
            receipt.write_text(json.dumps({"metadata": metadata, "execution_sha": args.execution_sha,
                                           "workflow_manifest": manifest}) + "\n")
            write_outputs(env["GITHUB_OUTPUT"], {"receipt": receipt})


if __name__ == "__main__":
    main()
