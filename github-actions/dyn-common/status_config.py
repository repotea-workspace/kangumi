"""Load trusted receiver configuration without duplicate keys or YAML objects."""

import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))
import yaml
from yaml.events import AliasEvent, CollectionEndEvent, CollectionStartEvent

from source_metadata import POLICY, REPOSITORY
from status_policy import load_policy


SECRET_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
OWNER = re.compile(r"^[A-Za-z0-9-]+$")


def unique_mapping(pairs):
    value = {}
    for key, item in pairs:
        if not isinstance(key, str) or key in value:
            raise ValueError("status configuration requires unique string keys")
        value[key] = item
    return value


class ConfigLoader(yaml.SafeLoader):
    pass


def _mapping(loader, node):
    return unique_mapping(
        (loader.construct_object(key, deep=True), loader.construct_object(value, deep=True))
        for key, value in node.value
    )


ConfigLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def load_config(path):
    path = Path(path)
    # Already queued receiver workflows may still pass the old path while
    # checking out the newly migrated default branch.
    if path.suffix == ".json" and not path.exists() and path.with_suffix(".yml").is_file():
        path = path.with_suffix(".yml")
    raw = path.read_bytes()
    if len(raw) > 1024 * 1024:
        raise ValueError("status configuration is too large")
    try:
        text = raw.decode("utf-8-sig")
        if path.suffix == ".json":
            # Existing @main callers can migrate after the shared action lands.
            config = json.loads(text, object_pairs_hook=unique_mapping)
        elif path.suffix in (".yml", ".yaml"):
            depth = 0
            for count, event in enumerate(yaml.parse(text, Loader=ConfigLoader)):
                if isinstance(event, AliasEvent):
                    raise ValueError("status configuration aliases are not supported")
                if isinstance(event, CollectionStartEvent):
                    depth += 1
                elif isinstance(event, CollectionEndEvent):
                    depth -= 1
                if depth > 100 or count > 10000:
                    raise ValueError("status configuration is too complex")
            config = yaml.load(text, Loader=ConfigLoader)
        else:
            raise ValueError("status configuration must be YAML or legacy JSON")
    except (UnicodeError, json.JSONDecodeError, yaml.YAMLError, RecursionError) as error:
        raise ValueError("invalid status configuration") from error
    if not isinstance(config, dict):
        raise ValueError("status configuration must be a mapping")
    return config


def validate_config(config, execution_repository, require_secrets=False):
    if (not isinstance(config, dict)
            or type(config.get("schema_version")) is not int
            or config["schema_version"] != 1
            or not isinstance(execution_repository, str)
            or not REPOSITORY.fullmatch(execution_repository)
            or config.get("execution_repository") != execution_repository):
        raise ValueError("invalid trusted status configuration")
    groups = config.get("credential_groups")
    if not isinstance(groups, dict) or not groups:
        raise ValueError("credential groups are required")
    owners_seen = set()
    for key, group in groups.items():
        if not isinstance(key, str) or not POLICY.fullmatch(key) or not isinstance(group, dict):
            raise ValueError("invalid credential group")
        owners = group.get("owners")
        if not isinstance(owners, list) or not owners:
            raise ValueError("credential group requires valid source owners")
        for owner in owners:
            if not isinstance(owner, str) or not OWNER.fullmatch(owner):
                raise ValueError("credential group requires valid source owners")
            normalized = owner.lower()
            if normalized in owners_seen:
                raise ValueError("source owner belongs to multiple credential groups")
            owners_seen.add(normalized)
        secret = group.get("secret_name")
        if secret is not None or require_secrets:
            if (not isinstance(secret, str) or not SECRET_NAME.fullmatch(secret)
                    or secret.upper().startswith("GITHUB_")):
                raise ValueError("credential group requires a valid secret_name")
    reporting = config.get("source_reporting", [])
    if (not isinstance(reporting, list)
            or any(not isinstance(repo, str) or not REPOSITORY.fullmatch(repo) for repo in reporting)
            or len({repo.lower() for repo in reporting}) != len(reporting)
            or any(repo.split("/", 1)[0].lower() not in owners_seen for repo in reporting)):
        raise ValueError("source reporting requires unique allowlisted repositories")
    sources = config.get("sources", {})
    if not isinstance(sources, dict):
        raise ValueError("trusted sources must be a mapping")
    repositories = set()
    for key in sources:
        if not isinstance(key, str):
            raise ValueError("invalid trusted source key")
        try:
            policy = load_policy(config, key, execution_repository)
        except (KeyError, TypeError, AttributeError) as error:
            raise ValueError("invalid trusted source policy") from error
        repository = policy["repository"].lower()
        if repository in repositories:
            raise ValueError("duplicate trusted source repository")
        repositories.add(repository)
    return config
