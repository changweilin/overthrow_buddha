from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = REPO_ROOT / "data" / "intel_archive"
ARTICLES_ROOT = ARCHIVE_ROOT / "articles"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def slugify(value: str, fallback: str = "item", max_length: int = 70) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[^\w\s.-]", " ", value, flags=re.UNICODE)
    value = re.sub(r"\s+", "-", value.strip().lower())
    value = value.strip("-._")
    if not value:
        value = fallback
    return value[:max_length].strip("-._") or fallback


def url_domain(url: str) -> str:
    return urlparse(url).netloc.lower()


def canonical_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    query = parsed.query
    return parsed._replace(scheme=scheme, netloc=netloc, path=path, query=query, fragment="").geturl()


def article_id(url: str) -> str:
    return sha256_text(canonical_url(url))[:16]


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def load_env_file(path: Path | None = None) -> None:
    env_path = path or (REPO_ROOT / ".env")
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def clean_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def looks_restricted_detail(text: str) -> bool:
    lowered = text.lower()
    patterns = [
        "how to build",
        "step-by-step",
        "wiring diagram",
        "detonator",
        "explosive payload",
        "target coordinates",
        "attack route",
        "arming mechanism",
        "munition assembly",
        "bypass geofence",
        "improvised explosive",
    ]
    return any(pattern in lowered for pattern in patterns)

