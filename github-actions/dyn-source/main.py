#!/usr/bin/env python3
"""Resolve, validate and match the dynamic source identity."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dyn-common"))
from source_metadata import (
    build_source_context,
    matches_ref,
    metadata_directory,
    parse_bool_flag,
    resolve_source_identity,
    write_outputs,
)


def main():
    env = os.environ
    directory = metadata_directory(env["GITHUB_WORKSPACE"])
    repository = env["EXPECTED_REPOSITORY"]
    sha, ref_type, ref_name = resolve_source_identity(directory, repository, env)
    matched = matches_ref(
        ref_type,
        ref_name,
        env.get("SOURCE_BRANCH_PATTERNS", ""),
        env.get("SOURCE_TAG_PATTERNS", ""),
    )
    outputs = {
        "sha": sha,
        "branch": ref_name if ref_type == "branch" else "",
        "tag": ref_name if ref_type == "tag" else "",
        "ref_type": ref_type,
        "ref_name": ref_name,
        "matches": str(matched).lower(),
        "repository": repository,
    }
    image_name = env.get("SOURCE_IMAGE_NAME", "").strip()
    enable_context = parse_bool_flag(
        env.get("SOURCE_CONTEXT_ENABLED", ""), "source_context"
    ) or bool(image_name)

    if enable_context:
        ctx_outputs, env_vars = build_source_context(
            repository,
            sha,
            ref_type,
            ref_name,
            run_number=env.get("GITHUB_RUN_NUMBER", ""),
            image_name=image_name,
            ghcr_registry=(
                env.get("SOURCE_GHCR_REGISTRY", "").strip()
                or env.get("DOCKER_REGISTRY", "").strip()
                or "ghcr.io"
            ),
            acr_registry=(
                env.get("SOURCE_ACR_REGISTRY", "").strip()
                or env.get("DOCKER_REGISTRY_ALI", "").strip()
            ),
            acr_namespace=env.get("SOURCE_ACR_NAMESPACE", "").strip() or "xoohub",
            server_url=env.get("GITHUB_SERVER_URL", "https://github.com"),
        )
        outputs.update(ctx_outputs)
        github_env = env.get("GITHUB_ENV", "")
        if github_env:
            write_outputs(github_env, env_vars)

    write_outputs(env["GITHUB_OUTPUT"], outputs)


if __name__ == "__main__":
    main()
