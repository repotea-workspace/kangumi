import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


COMMON = Path(__file__).resolve().parent.parent / "dyn-common"
sys.path.insert(0, str(COMMON))
from source_metadata import SCHEMA_VERSION, build_metadata, write_metadata


SCRIPT = Path(__file__).with_name("main.py")
CLONE_RESOLVE = Path(__file__).resolve().parent.parent / "clone-dyn" / "resolve.py"
SHA = "a" * 40
BASE_ENV = {
    "GITHUB_REPOSITORY": "owner/project",
    "GITHUB_REPOSITORY_ID": "10",
    "GITHUB_SHA": SHA,
    "GITHUB_REF_TYPE": "branch",
    "GITHUB_REF_NAME": "feature/api",
    "GITHUB_RUN_ID": "100",
    "GITHUB_RUN_ATTEMPT": "1",
    "GITHUB_WORKFLOW_REF": (
        "owner/project/.github/workflows/trigger.yml@refs/heads/main"
    ),
    "GITHUB_ACTOR": "octocat",
}
EVENT = {"repository": {"id": 10}, "head_commit": {"message": "Test"}}


def parse_outputs(path):
    if not path.exists():
        return {}
    lines = path.read_text(encoding="utf-8").splitlines()
    result = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if "<<" in line and ("=" not in line or line.index("<<") < line.index("=")):
            key, delimiter = line.split("<<", 1)
            i += 1
            body = []
            while i < len(lines) and lines[i] != delimiter:
                body.append(lines[i])
                i += 1
            result[key] = "\n".join(body)
        elif "=" in line:
            key, val = line.split("=", 1)
            result[key] = val
        i += 1
    return result


class DynamicSourceActionTest(unittest.TestCase):
    def run_action(self, workspace, branches="", tags="", extra_env=None):
        output = workspace / "output"
        gh_env = workspace / "github_env"
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "GITHUB_WORKSPACE": str(workspace),
            "GITHUB_OUTPUT": str(output),
            "GITHUB_ENV": str(gh_env),
            "GITHUB_API_URL": "https://api.github.com",
            "EXPECTED_REPOSITORY": "owner/project",
            "SOURCE_READ_TOKEN": "",
            "SOURCE_BRANCH_PATTERNS": branches,
            "SOURCE_TAG_PATTERNS": tags,
        }
        if extra_env:
            env.update(extra_env)
        subprocess.run(
            [sys.executable, str(SCRIPT)],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        return parse_outputs(output), parse_outputs(gh_env)

    def test_source_yml_outputs_and_branch_matching_default_mode_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            metadata_dir = workspace / ".github"
            metadata_dir.mkdir()
            metadata = build_metadata(
                BASE_ENV,
                EVENT,
                "executor",
                None,
                schema_version=SCHEMA_VERSION,
                dispatched_at="2026-10-16T00:00:00Z",
            )
            write_metadata(metadata_dir, metadata, "source-yml")

            outputs, gh_env = self.run_action(workspace, branches="main\nfeature/*")
            self.assertEqual(outputs["sha"], SHA)
            self.assertEqual(outputs["ref_type"], "branch")
            self.assertEqual(outputs["ref_name"], "feature/api")
            self.assertEqual(outputs["branch"], "feature/api")
            self.assertEqual(outputs["tag"], "")
            self.assertEqual(outputs["matches"], "true")
            self.assertNotIn("source_repo", outputs)
            self.assertEqual(gh_env, {})

    def test_tag_does_not_match_branch_filter(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            metadata_dir = workspace / ".github"
            metadata_dir.mkdir()
            env = dict(BASE_ENV, GITHUB_REF_TYPE="tag", GITHUB_REF_NAME="main")
            metadata = build_metadata(
                env,
                EVENT,
                "executor",
                None,
                schema_version=SCHEMA_VERSION,
                dispatched_at="2026-10-16T00:00:00Z",
            )
            write_metadata(metadata_dir, metadata, "source-yml")

            outputs, _ = self.run_action(workspace, branches="main")
            self.assertEqual(outputs["branch"], "")
            self.assertEqual(outputs["tag"], "main")
            self.assertEqual(outputs["matches"], "false")

    def test_legacy_full_sha_does_not_need_api_resolution(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            metadata_dir = workspace / ".github"
            metadata_dir.mkdir()
            (metadata_dir / "repository.txt").write_text("owner/project\n")
            (metadata_dir / "commit.txt").write_text(SHA + "\n")
            (metadata_dir / "branch.txt").write_text("main\n")

            outputs, _ = self.run_action(workspace, branches="main")
            self.assertEqual(outputs["sha"], SHA)
            self.assertEqual(outputs["matches"], "true")

    def test_opt_in_source_context_and_clone_dyn_resolve(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            metadata_dir = workspace / ".github"
            metadata_dir.mkdir()
            metadata = build_metadata(
                dict(BASE_ENV, GITHUB_REF_NAME="main"),
                EVENT,
                "executor",
                None,
                schema_version=SCHEMA_VERSION,
                dispatched_at="2026-10-16T00:00:00Z",
            )
            write_metadata(metadata_dir, metadata, "source-yml")

            outputs, gh_env = self.run_action(
                workspace,
                branches="main",
                extra_env={
                    "SOURCE_CONTEXT_ENABLED": "true",
                    "SOURCE_IMAGE_NAME": "coreprint-metasequoia",
                    "GITHUB_RUN_NUMBER": "42",
                    "DOCKER_REGISTRY_ALI": "registry.cn-hongkong.aliyuncs.com",
                },
            )
            self.assertEqual(outputs["source_repo"], "owner/project")
            self.assertEqual(outputs["repo_name"], "owner_project")
            self.assertEqual(outputs["short_sha"], "aaaaaaa")
            self.assertEqual(
                outputs["ghcr_sha_run"],
                "ghcr.io/owner/project/coreprint-metasequoia:sha-aaaaaaa-42",
            )
            self.assertEqual(
                outputs["ghcr_tags"].splitlines(),
                [
                    "ghcr.io/owner/project/coreprint-metasequoia:sha-aaaaaaa-42",
                    "ghcr.io/owner/project/coreprint-metasequoia:sha-aaaaaaa",
                    "ghcr.io/owner/project/coreprint-metasequoia:staging",
                ],
            )
            self.assertIn(
                "org.opencontainers.image.source=https://github.com/owner/project",
                outputs["oci_labels"],
            )
            self.assertEqual(
                outputs["ali_sha"],
                "registry.cn-hongkong.aliyuncs.com/xoohub/owner_project_coreprint-metasequoia:sha-aaaaaaa",
            )
            self.assertEqual(gh_env["SOURCE_REPO"], "owner/project")
            self.assertEqual(gh_env["REPO_NAME"], "owner_project")
            self.assertEqual(gh_env["SHORT_SHA"], "aaaaaaa")
            self.assertEqual(gh_env["SHA"], "aaaaaaa")

            # Also verify clone-dyn/resolve.py opt-in and default behavior
            c_out = workspace / "clone_out"
            c_env = workspace / "clone_env"
            subprocess.run(
                [sys.executable, str(CLONE_RESOLVE)],
                check=True,
                env={
                    **os.environ,
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "GITHUB_WORKSPACE": str(workspace),
                    "GITHUB_OUTPUT": str(c_out),
                    "GITHUB_ENV": str(c_env),
                    "SOURCE_REPOSITORY": "owner/project",
                    "SOURCE_CONTEXT_ENABLED": "true",
                    "SOURCE_IMAGE_NAME": "coreprint-sequoia",
                    "GITHUB_RUN_NUMBER": "42",
                },
            )
            clone_outputs = parse_outputs(c_out)
            self.assertEqual(clone_outputs["GIT_REF"], SHA)
            self.assertEqual(
                clone_outputs["ghcr_sha_run"],
                "ghcr.io/owner/project/coreprint-sequoia:sha-aaaaaaa-42",
            )


if __name__ == "__main__":
    unittest.main()
