from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value.isdigit():
        return int(value)
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _parse_simple_sources_yaml(text: str) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_key: str | None = None
    anchors: dict[str, Any] = {}
    key_anchors: dict[str, str] = {}

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if line == "sources:":
            continue

        if indent == 2 and line.startswith("- "):
            current = {}
            sources.append(current)
            current_key = None
            key_anchors = {}
            rest = line[2:].strip()
            if rest and ":" in rest:
                key, value = rest.split(":", 1)
                current[key.strip()] = _parse_scalar(value)
                current_key = key.strip()
            continue

        if current is None:
            continue

        if indent == 4 and ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value.startswith("*"):
                anchored = anchors.get(value[1:], [])
                if isinstance(anchored, list):
                    current[key] = list(anchored)
                elif isinstance(anchored, dict):
                    current[key] = dict(anchored)
                else:
                    current[key] = anchored
            elif value.startswith("&"):
                current[key] = []
                anchors[value[1:]] = current[key]
                key_anchors[key] = value[1:]
            elif value:
                current[key] = _parse_scalar(value)
            else:
                current[key] = []
            current_key = key
            continue

        if indent == 6 and current_key:
            if line.startswith("- "):
                if not isinstance(current.get(current_key), list):
                    current[current_key] = []
                current[current_key].append(_parse_scalar(line[2:].strip()))
            elif ":" in line:
                if not isinstance(current.get(current_key), dict):
                    current[current_key] = {}
                    if current_key in key_anchors:
                        anchors[key_anchors[current_key]] = current[current_key]
                key, value = line.split(":", 1)
                current[current_key][key.strip()] = _parse_scalar(value)

    return {"sources": sources}


def load_sources(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
    except Exception:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = _parse_simple_sources_yaml(text)
    sources = data.get("sources", []) if isinstance(data, dict) else []
    if not isinstance(sources, list):
        raise ValueError(f"Invalid sources config in {path}")
    return sources
