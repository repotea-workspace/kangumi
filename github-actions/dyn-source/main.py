#!/usr/bin/env python3
"""Resolve the source identity and expose safe Action outputs."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dyn-common"))
from github_api import GitHub
from source_metadata import SHA, metadata_directory, read_metadata, write_outputs


def main():
    env = os.environ
    directory = metadata_directory(env["GITHUB_WORKSPACE"])
    repository = env["EXPECTED_REPOSITORY"]
    metadata = read_metadata(directory, repository)
    if metadata:
        source = metadata["source"]
        sha = source["sha"]
        branch = source["ref_name"] if source["ref_type"] == "branch" else ""
    else:
        if (directory / "repository.txt").read_text().strip() != repository:
            raise ValueError("legacy source repository mismatch")
        ref = (directory / "commit.txt").read_text().strip()
        import re
        if not re.fullmatch(r"[0-9a-f]{7,40}", ref):
            raise ValueError("invalid legacy source SHA")
        api = GitHub(env.get("SOURCE_READ_TOKEN", ""), env["GITHUB_API_URL"])
        sha = api.get(f"/repos/{repository}/commits/{ref}")["sha"]
        branch_file = directory / "branch.txt"
        branch = branch_file.read_text().strip() if branch_file.exists() else ""
    if not SHA.fullmatch(sha):
        raise ValueError("source SHA did not resolve to a full commit")
    write_outputs(env["GITHUB_OUTPUT"], {"sha": sha, "branch": branch, "repository": repository})


if __name__ == "__main__":
    main()
