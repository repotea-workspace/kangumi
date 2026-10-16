import unittest

from workflow_identity import declared_workflow_name, workflow_contexts


class WorkflowIdentityTests(unittest.TestCase):
    def test_static_yaml_scalar_forms(self):
        cases = {
            b"name: Build # visible comment\non: push\n": "Build",
            b"'name': Build:Image\r\non: push\r\n": "Build:Image",
            b"name: 'Build #1: image'\non: push\n": "Build #1: image",
            b'name: "Build \\u2603"\non: push\n': "Build ☃",
            b'name: "Build\\Limage"\non: push\n': "Build image",
            b"name: >-\n  Build\n  image\non: push\n": "Build image",
            b"name: |-\n  Build image\non: push\n": "Build image",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(declared_workflow_name(raw), expected)

    def test_aliases_in_jobs_and_name_are_supported_without_constructing_jobs(self):
        nested = b"defaults: &job\n  runs-on: ubuntu-latest\nname: Build\njobs:\n  check: *job\n"
        aliased_name = b"title: &title Checks\nname: *title\non: push\n"
        self.assertEqual(declared_workflow_name(nested), "Build")
        self.assertEqual(declared_workflow_name(aliased_name), "Checks")

    def test_resource_bounds_fail_closed_to_filename(self):
        oversized = b"name: Build\n#" + b"x" * (1024 * 1024)
        deep = "name: Build\nroot:\n" + "".join(
            "  " * depth + "level:\n" for depth in range(1, 102)
        )
        contexts = workflow_contexts({
            ".github/workflows/oversized.yml": oversized,
            ".github/workflows/deep.yml": deep.encode(),
        })
        self.assertEqual(contexts[".github/workflows/oversized.yml"], "dynamic / oversized.yml")
        self.assertEqual(contexts[".github/workflows/deep.yml"], "dynamic / deep.yml")

    def test_nested_name_does_not_override_top_level_name(self):
        raw = b"jobs:\n  check:\n    name: Job name\nname: Workflow name\non: push\n"
        self.assertEqual(declared_workflow_name(raw), "Workflow name")

    def test_invalid_duplicate_or_missing_name_falls_back_to_filename(self):
        workflows = {
            ".github/workflows/no-name.yml": b"on: push\njobs: {}\n",
            ".github/workflows/duplicate.yml": b"name: First\nname: Second\n",
            ".github/workflows/invalid.yml": b"name: [not, scalar]\n",
        }
        contexts = workflow_contexts(workflows)
        self.assertEqual(contexts[".github/workflows/no-name.yml"], "dynamic / no-name.yml")
        self.assertEqual(contexts[".github/workflows/duplicate.yml"], "dynamic / duplicate.yml")
        self.assertEqual(contexts[".github/workflows/invalid.yml"], "dynamic / invalid.yml")

    def test_duplicate_names_append_filename_and_long_names_are_stable(self):
        duplicate = {
            ".github/workflows/a.yml": b"name: Checks\n",
            ".github/workflows/b.yml": b"name: Checks\n",
        }
        contexts = workflow_contexts(duplicate)
        self.assertEqual(contexts[".github/workflows/a.yml"], "dynamic / Checks (a.yml)")
        self.assertEqual(contexts[".github/workflows/b.yml"], "dynamic / Checks (b.yml)")

        long_name = "a" * 150
        path = ".github/workflows/long.yml"
        first = workflow_contexts({path: ("name: " + long_name + "\n").encode()})[path]
        second = workflow_contexts({path: ("name: " + long_name + "\n").encode()})[path]
        self.assertEqual(first, second)
        self.assertEqual(len(first), 100)

    def test_filename_suffix_collision_is_disambiguated_by_stable_path(self):
        workflows = {
            ".github/workflows/bar.yml": b"name: foo\n",
            ".github/workflows/baz.yml": b"name: foo\n",
            ".github/workflows/third.yml": b"name: foo (bar.yml)\n",
        }
        first = workflow_contexts(workflows)
        second = workflow_contexts(workflows)
        self.assertEqual(first, second)
        self.assertEqual(len({value.casefold() for value in first.values()}), 3)
        self.assertTrue(first[".github/workflows/bar.yml"].startswith("dynamic / foo (bar.yml) ["))
        self.assertTrue(first[".github/workflows/third.yml"].startswith("dynamic / foo (bar.yml) ["))


if __name__ == "__main__":
    unittest.main()
