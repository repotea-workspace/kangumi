#!/usr/bin/env python3
"""Wire the source workflow_run failure observer."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dyn-common"))
from dispatch import finalize_failed_trigger
from github_api import GitHub


def main():
    env = os.environ
    api = GitHub(env["SOURCE_STATUS_TOKEN"], env["GITHUB_API_URL"])
    event = json.loads(Path(env["GITHUB_EVENT_PATH"]).read_text())
    finalize_failed_trigger(api, env, event, env["TRIGGER_WORKFLOW"])


if __name__ == "__main__":
    main()
