"""Trusted YAML configuration and single-group routing regressions."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from receiver import route_group
from source_metadata import build_metadata
from status_config import load_config, validate_config
from test_protocol import ENV, EXEC_SHA, FakeAPI


CONFIG = {
    "schema_version": 1,
    "execution_repository": "executor/dynamic-actions",
    "credential_groups": {
        "one": {"owners": ["owner"], "secret_name": "SOURCE_TOKEN"},
        "two": {"owners": ["another"], "secret_name": "ANOTHER_TOKEN"},
    },
    "sources": {},
}
YAML = """schema_version: 1
execution_repository: executor/dynamic-actions
credential_groups:
  one:
    owners: [owner]
    secret_name: SOURCE_TOKEN
  two:
    owners:
      - another
    secret_name: ANOTHER_TOKEN
sources: {}
"""


class StatusConfigTests(unittest.TestCase):
    def load(self, text, suffix=".yml"):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / ("config" + suffix)
            path.write_text(text)
            return load_config(path)

    def test_yaml_and_legacy_json_are_equivalent(self):
        for suffix, text in ((".yml", YAML), (".json", json.dumps(CONFIG))):
            config = self.load(text, suffix)
            self.assertEqual(validate_config(config, CONFIG["execution_repository"], True), CONFIG)

    def test_queued_legacy_path_reads_migrated_yaml_but_does_not_hide_bad_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "dynamic-status.yml").write_text(YAML)
            old = root / "dynamic-status.json"
            self.assertEqual(load_config(old), CONFIG)
            old.write_text("{broken")
            with self.assertRaises(ValueError):
                load_config(old)

    def test_duplicate_keys_objects_aliases_and_non_string_keys_fail(self):
        for text in (
            YAML + "schema_version: 1\n",
            YAML.replace("owners: [owner]", "owners: [owner]\n    owners: [another]"),
            "!!python/object/apply:os.system ['false']",
            "a: &shared {}\nb: *shared\n",
            "1: value\n",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.load(text)
        with self.assertRaises(ValueError):
            self.load('{"schema_version":1,"schema_version":1}', ".json")

    def test_ambiguous_owners_and_invalid_secrets_fail_closed(self):
        for secret in ("GITHUB_TOKEN", "TOKEN\nINJECTED=true", "${{ secrets.OTHER }}", "", None):
            config = copy.deepcopy(CONFIG)
            config["credential_groups"]["one"]["secret_name"] = secret
            with self.subTest(secret=secret), self.assertRaises(ValueError):
                validate_config(config, CONFIG["execution_repository"], True)
        config = copy.deepcopy(CONFIG)
        config["credential_groups"]["two"]["owners"] = ["OWNER"]
        with self.assertRaises(ValueError):
            validate_config(config, CONFIG["execution_repository"])
        config = copy.deepcopy(CONFIG)
        config["schema_version"] = True
        with self.assertRaises(ValueError):
            validate_config(config, CONFIG["execution_repository"])

    def test_route_uses_only_trusted_secret_mapping(self):
        api = FakeAPI()
        metadata = build_metadata(ENV, {"repository": {"id": 10}}, "executor", "")
        api.files[("executor/dynamic-actions", ".github/source.json", EXEC_SHA)] = json.dumps(metadata).encode()
        self.assertEqual(
            route_group(api, "executor/dynamic-actions", CONFIG, EXEC_SHA),
            {"matched": "true", "group": "one", "secret_name": "SOURCE_TOKEN", "execution_sha": EXEC_SHA},
        )
        metadata["source"]["repository"] = "unregistered/project"
        api.files[("executor/dynamic-actions", ".github/source.json", EXEC_SHA)] = json.dumps(metadata).encode()
        self.assertEqual(route_group(api, "executor/dynamic-actions", CONFIG, EXEC_SHA)["matched"], "false")

    def test_wrong_execution_or_injected_metadata_cannot_select_secret(self):
        api = FakeAPI()
        metadata = build_metadata(ENV, {"repository": {"id": 10}}, "executor", "")
        metadata["secret_name"] = "ANOTHER_TOKEN"
        api.files[("executor/dynamic-actions", ".github/source.json", EXEC_SHA)] = json.dumps(metadata).encode()
        with self.assertRaises(ValueError):
            route_group(api, "executor/dynamic-actions", CONFIG, EXEC_SHA)
        with self.assertRaises(ValueError):
            route_group(api, "other/dynamic-actions", CONFIG, EXEC_SHA)
