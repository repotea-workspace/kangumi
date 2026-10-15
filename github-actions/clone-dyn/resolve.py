#!/usr/bin/env python3
"""Select an immutable forwarded revision before the workspace is replaced."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dyn-common"))
from source_metadata import checkout_ref, write_outputs


def main():
    env = os.environ
    ref = checkout_ref(env["GITHUB_WORKSPACE"], env["SOURCE_REPOSITORY"],
                       env.get("SOURCE_REF", ""), env.get("SOURCE_REF_FILE", ""))
    write_outputs(env["GITHUB_OUTPUT"], {"GIT_REF": ref})


if __name__ == "__main__":
    main()
