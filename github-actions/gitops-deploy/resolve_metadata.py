#!/usr/bin/env python3
"""Resolve dynamic source metadata and build the GitOps commit message."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dyn-common"))
from source_metadata import metadata_directory, read_metadata, write_outputs


def _text(path):
    return path.read_text(encoding="utf-8").strip() if path.is_file() else ""


def _input_or_file(value):
    if not value:
        return ""
    path = Path(value)
    return _text(path) if path.is_file() else value


def _commit_message(env, repository, ref_name, commit_id, message, authors, dispatch_time):
    subject = message.splitlines()[0][:60] if message else ""
    if len(subject) >= 60:
        subject += "..."

    links = [
        f"    - https://github.com/{env['EXECUTION_REPOSITORY']}/commit/{env['EXECUTION_SHA']}"
    ]
    if ref_name:
        links.append(f"    - https://github.com/{repository}/tree/{ref_name}")
    if commit_id:
        links.append(f"    - https://github.com/{repository}/commit/{commit_id}")

    lines = [
        f"[{repository}] {ref_name} :: {subject}",
        "",
        "--- Commit Message ---",
        message,
        "",
        "--- Actions Context ---",
        f"* Repository: https://github.com/{repository}",
        f"* Git Ref: {ref_name}",
    ]
    if authors:
        lines.append(f"* Author: {authors}")
    if dispatch_time:
        lines.append(f"* Dispatch Time: {dispatch_time}")
    lines.extend((
        f"* Build started at: {env.get('BUILD_STARTED_AT', '')}",
        f"* Source: {env['EVENT_NAME']}",
        f"* Workflows: https://github.com/{env['EXECUTION_REPOSITORY']}/actions/runs/{env['RUN_ID']}",
        "* Commits:",
        "\n".join(links),
    ))
    return "\n".join(lines)


def main():
    env = os.environ
    directory = metadata_directory(env["GITHUB_WORKSPACE"])
    metadata = read_metadata(directory)

    source = metadata["source"] if metadata else {}
    commit = metadata.get("commit", {}) if metadata else {}
    dispatch = metadata.get("dispatch", {}) if metadata else {}

    message = _input_or_file(env.get("INPUT_COMMIT_MESSAGE", ""))
    if not message:
        message = commit.get("message") or _text(directory / "message.txt")

    ref_name = _input_or_file(env.get("INPUT_AC_GIT_REF", ""))
    if not ref_name:
        ref_name = source.get("ref_name") or _text(directory / "ref.txt")

    commit_id = _input_or_file(env.get("INPUT_COMMIT_ID", ""))
    if not commit_id:
        commit_id = source.get("sha") or _text(directory / "commit.txt")

    repository = env.get("INPUT_SOURCE_REPOSITORY", "")
    if not repository:
        repository = (
            source.get("repository")
            or _text(directory / "repository.txt")
            or env["FALLBACK_REPOSITORY"]
        )

    authors = commit.get("authors")
    author_text = (
        "\n".join("@" + author for author in authors)
        if authors else _text(directory / "author.txt")
    )
    dispatch_time = dispatch.get("created_at") or _text(directory / "date.txt")
    commit_message = _commit_message(
        env, repository, ref_name, commit_id, message, author_text, dispatch_time
    )

    write_outputs(env["GITHUB_OUTPUT"], {
        "message": message,
        "ref_name": ref_name,
        "commit_id": commit_id,
        "repository": repository,
        "authors": author_text,
        "dispatch_time": dispatch_time,
        "commit_message": commit_message,
    })


if __name__ == "__main__":
    main()
