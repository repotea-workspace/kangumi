#!/usr/bin/env python3
"""CLI wiring for source-owned forwarding receipts."""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dyn-common"))
from dispatch import finish_dispatch, prepare_dispatch
from github_api import GitHub
from source_metadata import read_metadata


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


if __name__ == "__main__":
    main()
