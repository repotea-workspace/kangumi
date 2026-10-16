import json
import tempfile
import unittest
from pathlib import Path

from source_metadata import (
    LEGACY_SCHEMA_VERSION,
    SCHEMA_VERSION,
    build_metadata,
    load_metadata,
    matches_ref,
    read_metadata,
    write_metadata,
)
from source_yaml import dumps as dump_source_yaml


SHA = "a" * 40
ENV = {
    "GITHUB_REPOSITORY": "owner/project",
    "GITHUB_REPOSITORY_ID": "10",
    "GITHUB_SHA": SHA,
    "GITHUB_REF_TYPE": "branch",
    "GITHUB_REF_NAME": "feature/source-v2",
    "GITHUB_RUN_ID": "100",
    "GITHUB_RUN_ATTEMPT": "2",
    "GITHUB_WORKFLOW_REF": (
        "owner/project/.github/workflows/trigger.yml@refs/heads/main"
    ),
    "GITHUB_ACTOR": "fallback-user",
}
EVENT = {
    "repository": {"id": 10},
    "head_commit": {
        "message": "标题: ship #1\n\nLong body",
        "author": {"username": "fallback-user"},
    },
    "commits": [
        {"author": {"username": "alice"}},
        {"author": {"username": "bob"}},
    ],
}


class SourceMetadataV2Tests(unittest.TestCase):
    def test_source_yml_round_trip_preserves_multiline_and_identity(self):
        metadata = build_metadata(
            ENV,
            EVENT,
            "executor",
            "checks-v1",
            schema_version=SCHEMA_VERSION,
            dispatched_at="2026-10-16T10:20:30Z",
        )
        raw = dump_source_yaml(metadata)
        self.assertEqual(load_metadata(raw, "source.yml"), metadata)
        self.assertIn('message: "', raw)
        self.assertEqual(metadata["commit"]["authors"], ["alice", "bob"])

        metadata["commit"]["message"] = "next\u0085line\u2028paragraph\u2029end"
        escaped = dump_source_yaml(metadata)
        self.assertNotIn("\u0085", escaped)
        self.assertNotIn("\u2028", escaped)
        self.assertNotIn("\u2029", escaped)
        self.assertEqual(load_metadata(escaped, "source.yml"), metadata)

    def test_windows_checkout_crlf_preserves_source_metadata(self):
        metadata = build_metadata(
            ENV, EVENT, "executor", None, schema_version=SCHEMA_VERSION,
            dispatched_at="2026-10-16T10:20:30Z",
        )
        canonical = dump_source_yaml(metadata)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "source.yml").write_bytes(canonical.replace("\n", "\r\n").encode())
            self.assertEqual(read_metadata(directory), metadata)
        with self.assertRaises(ValueError):
            load_metadata(canonical.replace("\n", "\r", 1), "source.yml")

    def test_boolean_schema_version_is_rejected(self):
        metadata = build_metadata(
            ENV, EVENT, "executor", None, schema_version=LEGACY_SCHEMA_VERSION
        )
        metadata["schema_version"] = True
        with self.assertRaises(ValueError):
            load_metadata(json.dumps(metadata).encode(), "source.json")

    def test_non_mapping_legacy_json_is_rejected_as_invalid_metadata(self):
        for raw in (b"[]", b"null", b'"text"'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                load_metadata(raw, "source.json")

    def test_legacy_json_remains_accepted(self):
        metadata = build_metadata(
            ENV, EVENT, "executor", None, schema_version=LEGACY_SCHEMA_VERSION
        )
        raw = json.dumps(metadata).encode()
        self.assertEqual(load_metadata(raw, "source.json"), metadata)

    def test_invalid_source_yml_never_falls_back_to_valid_json(self):
        legacy = build_metadata(
            ENV, EVENT, "executor", None, schema_version=LEGACY_SCHEMA_VERSION
        )
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "source.yml").write_text(
                "schema_version: 2\nsource: &identity {}\n",
                encoding="utf-8",
            )
            (directory / "source.json").write_text(json.dumps(legacy), encoding="utf-8")
            with self.assertRaises(ValueError):
                read_metadata(directory)

    def test_writer_emits_only_the_selected_format(self):
        v2 = build_metadata(
            ENV,
            EVENT,
            "executor",
            None,
            schema_version=SCHEMA_VERSION,
            dispatched_at="2026-10-16T10:20:30Z",
        )
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            write_metadata(directory, v2, "source-yml")
            self.assertTrue((directory / "source.yml").is_file())
            self.assertFalse((directory / "source.json").exists())

    def test_branch_and_tag_filters_are_type_safe(self):
        self.assertTrue(matches_ref("branch", "main", branches="main"))
        self.assertTrue(matches_ref("branch", "feature/api", branches="main\nfeature/*"))
        self.assertFalse(matches_ref("branch", "feature/api", tags="feature/*"))
        self.assertTrue(matches_ref("tag", "v1.2.3", tags="v?.*"))
        self.assertFalse(matches_ref("tag", "main", branches="main"))
        self.assertTrue(matches_ref("branch", "anything"))

    def test_invalid_patterns_fail_instead_of_becoming_nonmatches(self):
        for value in (" main", "main ", "release[0-9]", "bad ref"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                matches_ref("branch", "main", branches=value)


if __name__ == "__main__":
    unittest.main()
