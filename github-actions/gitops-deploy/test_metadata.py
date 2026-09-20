import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("metadata.sh")
ACTION = Path(__file__).with_name("action.yml")


class MetadataDirectoryTest(unittest.TestCase):
    def resolve(self, workspace: Path) -> str:
        return subprocess.run(
            ["bash", "-c", 'source "$1"; gitops_metadata_dir', "bash", str(SCRIPT)],
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "GITHUB_WORKSPACE": str(workspace)},
        ).stdout.strip()

    def test_supports_direct_and_clone_dyn_workspaces(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / ".github").mkdir()
            self.assertEqual(self.resolve(workspace), str(workspace / ".github"))

            (workspace / "__origin__" / ".github").mkdir(parents=True)
            self.assertEqual(self.resolve(workspace), str(workspace / "__origin__" / ".github"))

        action = ACTION.read_text(encoding="utf-8")
        self.assertIn('source "${GITHUB_ACTION_PATH}/metadata.sh"', action)
        for name in ("message.txt", "ref.txt", "commit.txt", "date.txt", "author.txt", "repository.txt"):
            self.assertIn(f'${{METADATA_DIR}}/{name}', action)


if __name__ == "__main__":
    unittest.main()
