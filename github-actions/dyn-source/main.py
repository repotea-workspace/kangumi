#!/usr/bin/env python3
"""Resolve, validate and match the dynamic source identity."""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dyn-common"))
from github_api import GitHub
from source_metadata import (REPOSITORY, SHA, matches_ref, metadata_directory,
                             read_metadata, write_outputs)


SHORT_SHA = re.compile(r"^[0-9a-f]{7,39}$")


def _legacy_scalar(path):
    raw = path.read_text(encoding="utf-8")
    value = raw.strip()
    if not value or "\n" in value or "\r" in value:
        raise ValueError(f"invalid legacy {path.name}")
    return value


def _legacy_source(directory, repository, env):
    if not REPOSITORY.fullmatch(repository):
        raise ValueError("invalid expected source repository")
    if _legacy_scalar(directory / "repository.txt") != repository:
        raise ValueError("legacy source repository mismatch")

    sha = _legacy_scalar(directory / "commit.txt")
    if SHORT_SHA.fullmatch(sha):
        api = GitHub(env.get("SOURCE_READ_TOKEN", ""), env["GITHUB_API_URL"])
        sha = api.get(f"/repos/{repository}/commits/{sha}")["sha"]
    elif not SHA.fullmatch(sha):
        raise ValueError("invalid legacy source SHA")

    refs = [
        (ref_type, _legacy_scalar(path))
        for ref_type, path in (
            ("branch", directory / "branch.txt"),
            ("tag", directory / "tag.txt"),
        )
        if path.exists()
    ]
    if len(refs) != 1:
        raise ValueError("legacy metadata must identify exactly one branch or tag")
    ref_type, ref_name = refs[0]
    return sha, ref_type, ref_name


def main():
    env = os.environ
    directory = metadata_directory(env["GITHUB_WORKSPACE"])
    repository = env["EXPECTED_REPOSITORY"]
    metadata = read_metadata(directory, repository)
    if metadata:
        source = metadata["source"]
        sha = source["sha"]
        ref_type = source["ref_type"]
        ref_name = source["ref_name"]
    else:
        sha, ref_type, ref_name = _legacy_source(directory, repository, env)

    if not SHA.fullmatch(sha):
        raise ValueError("source SHA did not resolve to a full commit")
    matched = matches_ref(
        ref_type,
        ref_name,
        env.get("SOURCE_BRANCH_PATTERNS", ""),
        env.get("SOURCE_TAG_PATTERNS", ""),
    )
    write_outputs(env["GITHUB_OUTPUT"], {
        "sha": sha,
        "branch": ref_name if ref_type == "branch" else "",
        "tag": ref_name if ref_type == "tag" else "",
        "ref_type": ref_type,
        "ref_name": ref_name,
        "matches": str(matched).lower(),
        "repository": repository,
    })


if __name__ == "__main__":
    main()
