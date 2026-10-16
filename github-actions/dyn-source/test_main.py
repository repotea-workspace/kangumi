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
    return dict(
        line.split("=", 1)
        for line in path.read_text(encoding="utf-8").splitlines()
    )


class DynamicSourceActionTest(unittest.TestCase):
    def run_action(self, workspace, branches="", tags=""):
        output = workspace / "output"
        subprocess.run(
            ["python3", str(SCRIPT)],
            check=True,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "GITHUB_WORKSPACE": str(workspace),
                "GITHUB_OUTPUT": str(output),
                "GITHUB_API_URL": "https://api.github.com",
                "EXPECTED_REPOSITORY": "owner/project",
                "SOURCE_READ_TOKEN": "",
                "SOURCE_BRANCH_PATTERNS": branches,
                "SOURCE_TAG_PATTERNS": tags,
            },
        )
        return parse_outputs(output)

    def test_source_yml_outputs_and_branch_matching(self):
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

            outputs = self.run_action(workspace, branches="main\nfeature/*")
            self.assertEqual(outputs["sha"], SHA)
            self.assertEqual(outputs["ref_type"], "branch")
            self.assertEqual(outputs["ref_name"], "feature/api")
            self.assertEqual(outputs["branch"], "feature/api")
            self.assertEqual(outputs["tag"], "")
            self.assertEqual(outputs["matches"], "true")

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

            outputs = self.run_action(workspace, branches="main")
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

            outputs = self.run_action(workspace, branches="main")
            self.assertEqual(outputs["sha"], SHA)
            self.assertEqual(outputs["matches"], "true")


if __name__ == "__main__":
    unittest.main()
