import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


COMMON = Path(__file__).resolve().parent.parent / "dyn-common"
sys.path.insert(0, str(COMMON))
from source_metadata import SCHEMA_VERSION, build_metadata, write_metadata


SCRIPT = Path(__file__).with_name("resolve_metadata.py")
ACTION = Path(__file__).with_name("action.yml")
SOURCE_SHA = "a" * 40
ENV = {
    "GITHUB_REPOSITORY": "owner/project",
    "GITHUB_REPOSITORY_ID": "10",
    "GITHUB_SHA": SOURCE_SHA,
    "GITHUB_REF_TYPE": "branch",
    "GITHUB_REF_NAME": "main",
    "GITHUB_RUN_ID": "100",
    "GITHUB_RUN_ATTEMPT": "1",
    "GITHUB_WORKFLOW_REF": (
        "owner/project/.github/workflows/trigger.yml@refs/heads/main"
    ),
    "GITHUB_ACTOR": "octocat",
}
EVENT = {
    "repository": {"id": 10},
    "head_commit": {"message": "Ship metadata\n\nDetails", "author": {"username": "octocat"}},
    "commits": [{"author": {"username": "octocat"}}],
}


def read_outputs(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    outputs = {}
    index = 0
    while index < len(lines):
        key, separator, value = lines[index].partition("=")
        if separator:
            outputs[key] = value
            index += 1
            continue
        key, delimiter = lines[index].split("<<", 1)
        index += 1
        values = []
        while lines[index] != delimiter:
            values.append(lines[index])
            index += 1
        outputs[key] = "\n".join(values)
        index += 1
    return outputs


class MetadataResolutionTest(unittest.TestCase):
    def run_resolver(self, workspace):
        output = workspace / "outputs"
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
                "INPUT_SOURCE_REPOSITORY": "",
                "INPUT_COMMIT_MESSAGE": "",
                "INPUT_AC_GIT_REF": "",
                "INPUT_COMMIT_ID": "",
                "FALLBACK_REPOSITORY": "executor/dynamic-actions",
                "EXECUTION_REPOSITORY": "executor/dynamic-actions",
                "EXECUTION_SHA": "e" * 40,
                "BUILD_STARTED_AT": "2026-10-16T12:01:00Z",
                "EVENT_NAME": "push",
                "RUN_ID": "321",
            },
        )
        return read_outputs(output)

    def test_reads_source_yml_before_and_after_clone_dyn(self):
        for restored in (False, True):
            with self.subTest(restored=restored), tempfile.TemporaryDirectory() as temporary:
                workspace = Path(temporary)
                metadata_dir = workspace / ("__origin__/.github" if restored else ".github")
                metadata_dir.mkdir(parents=True)
                metadata = build_metadata(
                    ENV,
                    EVENT,
                    "executor",
                    None,
                    schema_version=SCHEMA_VERSION,
                    dispatched_at="2026-10-16T12:00:00Z",
                )
                write_metadata(metadata_dir, metadata, "source-yml")

                outputs = self.run_resolver(workspace)
                self.assertEqual(outputs["repository"], "owner/project")
                self.assertEqual(outputs["ref_name"], "main")
                self.assertEqual(outputs["commit_id"], SOURCE_SHA)
                self.assertEqual(outputs["message"], "Ship metadata\n\nDetails")
                self.assertEqual(outputs["authors"], "@octocat")
                self.assertEqual(outputs["dispatch_time"], "2026-10-16T12:00:00Z")

    def test_legacy_text_fallback_and_explicit_inputs_remain_supported(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            metadata_dir = workspace / ".github"
            metadata_dir.mkdir()
            values = {
                "repository.txt": "owner/project\n",
                "ref.txt": "release\n",
                "commit.txt": "abc1234\n",
                "message.txt": "Legacy message",
                "author.txt": "@legacy\n",
                "date.txt": "2026-10-15T00:00:00Z\n",
            }
            for name, value in values.items():
                (metadata_dir / name).write_text(value, encoding="utf-8")

            outputs = self.run_resolver(workspace)
            self.assertEqual(outputs["repository"], "owner/project")
            self.assertEqual(outputs["ref_name"], "release")
            self.assertEqual(outputs["commit_id"], "abc1234")
            self.assertEqual(outputs["message"], "Legacy message")

        action = ACTION.read_text(encoding="utf-8")
        self.assertIn('python3 "${GITHUB_ACTION_PATH}/resolve_metadata.py"', action)
        self.assertIn("steps.source-metadata.outputs.commit_message", action)
        self.assertNotIn("${METADATA_DIR}/message.txt", action)
        self.assertNotIn("message<<EOF", action)

    def test_commit_message_output_cannot_collide_with_fixed_delimiter(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            metadata_dir = workspace / ".github"
            metadata_dir.mkdir()
            metadata = build_metadata(
                ENV,
                EVENT,
                "executor",
                None,
                schema_version=SCHEMA_VERSION,
                dispatched_at="2026-10-16T12:00:00Z",
            )
            metadata["commit"]["message"] = "Subject\nEOF\nTail"
            write_metadata(metadata_dir, metadata, "source-yml")

            outputs = self.run_resolver(workspace)

            self.assertIn("--- Commit Message ---\nSubject\nEOF\nTail", outputs["commit_message"])
            self.assertIn("* Dispatch Time: 2026-10-16T12:00:00Z", outputs["commit_message"])
            self.assertIn(
                "https://github.com/executor/dynamic-actions/commit/" + "e" * 40,
                outputs["commit_message"],
            )


if __name__ == "__main__":
    unittest.main()
