from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import ARTICLES_ROOT, article_id, read_json, slugify, write_json


def article_folder(source_name: str, title: str, url: str) -> Path:
    source_slug = slugify(source_name, fallback="source", max_length=50)
    item_slug = slugify(title, fallback="article", max_length=70)
    return ARTICLES_ROOT / source_slug / f"{item_slug}-{article_id(url)}"


def find_article_by_url(url: str) -> Path | None:
    needle = article_id(url)
    if not ARTICLES_ROOT.exists():
        return None
    for metadata_path in ARTICLES_ROOT.glob(f"*/*-{needle}/metadata.json"):
        return metadata_path.parent
    return None


def read_metadata(folder: Path) -> dict[str, Any]:
    return read_json(folder / "metadata.json", {})


def write_metadata(folder: Path, metadata: dict[str, Any]) -> None:
    write_json(folder / "metadata.json", metadata)

