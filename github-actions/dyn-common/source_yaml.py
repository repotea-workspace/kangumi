"""Dependency-free, strict YAML subset for dynamic source metadata.

The writer emits ordinary YAML mappings whose scalar values use YAML's JSON
flow syntax. The parser intentionally accepts only that emitted subset: two
space indentation, simple mapping keys, JSON scalars, and nested mappings.
This keeps untrusted forwarded metadata inert without relying on packages from
the calling repository or runner image.
"""

import json
import re


MAX_METADATA_BYTES = 256 * 1024
KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
LINE = re.compile(r"^( *)([A-Za-z][A-Za-z0-9_]*):(.*)$")


def _scalar(value):
    if isinstance(value, (dict, tuple)):
        raise TypeError("nested metadata must use mappings and lists")
    if isinstance(value, list) and any(not isinstance(item, str) for item in value):
        raise TypeError("metadata lists may contain only strings")
    if not (value is None or isinstance(value, (bool, int, str, list))):
        raise TypeError("unsupported metadata scalar")
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def dumps(value):
    """Serialize a mapping in the strict source metadata YAML format."""
    if not isinstance(value, dict):
        raise TypeError("source metadata must be a mapping")
    lines = []

    def write(mapping, indent):
        if not mapping:
            raise TypeError("empty metadata mappings are not supported")
        for key, item in mapping.items():
            if not isinstance(key, str) or not KEY.fullmatch(key):
                raise TypeError("invalid metadata key")
            prefix = " " * indent + key + ":"
            if isinstance(item, dict):
                lines.append(prefix)
                write(item, indent + 2)
            else:
                lines.append(prefix + " " + _scalar(item))

    write(value, 0)
    encoded = ("\n".join(lines) + "\n").encode("utf-8")
    if len(encoded) > MAX_METADATA_BYTES:
        raise ValueError("dynamic source metadata is too large")
    return encoded.decode("utf-8")


def loads(raw):
    """Parse only the strict YAML subset emitted by :func:`dumps`."""
    if isinstance(raw, bytes):
        if len(raw) > MAX_METADATA_BYTES:
            raise ValueError("dynamic source metadata is too large")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("invalid dynamic source YAML encoding") from error
    elif isinstance(raw, str):
        if len(raw.encode("utf-8")) > MAX_METADATA_BYTES:
            raise ValueError("dynamic source metadata is too large")
        text = raw
    else:
        raise ValueError("dynamic source metadata must be text")
    if not text or not text.endswith("\n") or "\r" in text or "\t" in text:
        raise ValueError("invalid dynamic source YAML layout")

    root = {}
    stack = [(-2, root)]
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line:
            raise ValueError(f"blank line in dynamic source YAML at {line_number}")
        match = LINE.fullmatch(line)
        if not match:
            raise ValueError(f"invalid dynamic source YAML line {line_number}")
        spaces, key, remainder = match.groups()
        indent = len(spaces)
        if indent % 2:
            raise ValueError(f"invalid dynamic source YAML indentation at {line_number}")
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack or stack[-1][0] != indent - 2:
            raise ValueError(f"invalid dynamic source YAML nesting at {line_number}")
        mapping = stack[-1][1]
        if key in mapping:
            raise ValueError(f"duplicate dynamic source YAML key: {key}")
        if remainder == "":
            child = {}
            mapping[key] = child
            stack.append((indent, child))
            continue
        if not remainder.startswith(" ") or remainder.startswith("  "):
            raise ValueError(f"invalid dynamic source YAML scalar at {line_number}")
        try:
            value = json.loads(remainder[1:])
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid dynamic source YAML scalar at {line_number}") from error
        if isinstance(value, (dict, float)) or (
                isinstance(value, list) and any(not isinstance(item, str) for item in value)):
            raise ValueError(f"unsupported dynamic source YAML value at {line_number}")
        mapping[key] = value
    return root
