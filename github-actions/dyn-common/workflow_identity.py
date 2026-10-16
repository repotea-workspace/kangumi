"""Stable status contexts derived from exact forwarded workflow bytes."""

import hashlib
from pathlib import Path, PurePosixPath
import sys

VENDOR = Path(__file__).resolve().parent / "vendor"
sys.path.insert(0, str(VENDOR))
import yaml
from yaml.events import (
    AliasEvent,
    CollectionEndEvent,
    CollectionStartEvent,
    ScalarEvent,
)
from yaml.nodes import MappingNode, ScalarNode


MAX_WORKFLOW_BYTES = 1024 * 1024
MAX_YAML_DEPTH = 100
MAX_YAML_NODES = 10000
MAX_CONTEXT_LENGTH = 100


def _bounded_yaml(text):
    depth = 0
    nodes = 0
    for event in yaml.parse(text, Loader=yaml.SafeLoader):
        if isinstance(event, CollectionStartEvent):
            depth += 1
            nodes += 1
            if depth > MAX_YAML_DEPTH:
                raise ValueError("workflow YAML is nested too deeply")
        elif isinstance(event, CollectionEndEvent):
            depth -= 1
        elif isinstance(event, (ScalarEvent, AliasEvent)):
            nodes += 1
        if nodes > MAX_YAML_NODES:
            raise ValueError("workflow YAML has too many nodes")
    return yaml.compose(text, Loader=yaml.SafeLoader)


def declared_workflow_name(raw):
    """Return the normalized static top-level YAML name, or None if unavailable."""
    try:
        if isinstance(raw, bytes):
            if len(raw) > MAX_WORKFLOW_BYTES:
                return None
            text = raw.decode("utf-8-sig")
        elif isinstance(raw, str):
            if len(raw.encode("utf-8")) > MAX_WORKFLOW_BYTES:
                return None
            text = raw
        else:
            return None
        root = _bounded_yaml(text)
    except (UnicodeError, ValueError, yaml.YAMLError, RecursionError):
        return None
    if not isinstance(root, MappingNode):
        return None

    seen = set()
    name = None
    for key_node, value_node in root.value:
        if not isinstance(key_node, ScalarNode):
            return None
        key = (key_node.tag, key_node.value)
        if key in seen:
            return None
        seen.add(key)
        if key_node.value == "name":
            if not isinstance(value_node, ScalarNode):
                return None
            name = value_node.value
    if not isinstance(name, str):
        return None
    normalized = " ".join(name.split())
    return normalized or None


def _context(value):
    if len(value) <= MAX_CONTEXT_LENGTH:
        return value
    suffix = "-" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return value[:MAX_CONTEXT_LENGTH - len(suffix)] + suffix


def _path_context(label, path, digest_length=12):
    suffix = " [" + hashlib.sha256(path.encode("utf-8")).hexdigest()[:digest_length] + "]"
    prefix = "dynamic / " + label
    return prefix[:MAX_CONTEXT_LENGTH - len(suffix)] + suffix


def workflow_contexts(workflows):
    """Map exact workflow paths to stable, collision-free status contexts."""
    names = {}
    for path, raw in workflows.items():
        filename = PurePosixPath(path).name
        names[path] = declared_workflow_name(raw) or filename

    name_counts = {}
    for name in names.values():
        key = name.casefold()
        name_counts[key] = name_counts.get(key, 0) + 1

    labels = {}
    for path, name in names.items():
        filename = PurePosixPath(path).name
        labels[path] = name if name_counts[name.casefold()] == 1 else f"{name} ({filename})"

    contexts = {path: _context("dynamic / " + label) for path, label in labels.items()}
    context_counts = {}
    for context in contexts.values():
        key = context.casefold()
        context_counts[key] = context_counts.get(key, 0) + 1
    for path, context in tuple(contexts.items()):
        if context_counts[context.casefold()] > 1:
            contexts[path] = _path_context(labels[path], path)

    # A full path digest keeps reporting available even for an engineered
    # collision in the shorter suffix.
    final_counts = {}
    for context in contexts.values():
        key = context.casefold()
        final_counts[key] = final_counts.get(key, 0) + 1
    for path, context in tuple(contexts.items()):
        if final_counts[context.casefold()] > 1:
            contexts[path] = _path_context(labels[path], path, digest_length=64)
    return contexts
