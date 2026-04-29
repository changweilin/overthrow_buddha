from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from osint_core.storage import read_metadata
from osint_core.utils import ARCHIVE_ROOT, ARTICLES_ROOT, read_json, write_json

VIEWER_DATA_JS = Path(__file__).with_name("archive_index.js")


def relative(path: Path) -> str:
    return path.relative_to(ARCHIVE_ROOT).as_posix()


def summary_excerpt(folder: Path) -> str:
    path = folder / "summary.zh.md"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8").strip()
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]
    return " ".join(lines)[:500]


def build_index() -> dict[str, Any]:
    articles: list[dict[str, Any]] = []
    if ARTICLES_ROOT.exists():
        for metadata_path in sorted(ARTICLES_ROOT.glob("*/*/metadata.json")):
            folder = metadata_path.parent
            metadata = read_metadata(folder)
            if not metadata:
                continue
            first_image = ""
            for image in metadata.get("media", {}).get("images", []):
                if image.get("status") == "downloaded" and image.get("path"):
                    first_image = f"{relative(folder)}/{image['path']}"
                    break
            articles.append(
                {
                    "id": folder.name.rsplit("-", 1)[-1],
                    "title": metadata.get("title"),
                    "source": metadata.get("source"),
                    "url": metadata.get("url"),
                    "collected_at": metadata.get("collected_at"),
                    "updated_at": metadata.get("updated_at"),
                    "last_seen": metadata.get("last_seen"),
                    "restricted_detail": metadata.get("restricted_detail", False),
                    "summary_status": metadata.get("summary_status"),
                    "folder": relative(folder),
                    "original_md": f"{relative(folder)}/original.md",
                    "summary_zh_md": f"{relative(folder)}/summary.zh.md",
                    "image": first_image,
                    "summary_excerpt": summary_excerpt(folder),
                }
            )
    articles.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
    return {
        "generated_at": read_json(ARCHIVE_ROOT / "index.json", {}).get("generated_at"),
        "article_count": len(articles),
        "articles": articles,
    }


def write_viewer_data(path: Path, index: dict[str, Any]) -> None:
    payload = json.dumps(index, ensure_ascii=False, indent=2)
    path.write_text(f"window.ARCHIVE_INDEX = {payload};\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build archive index JSON")
    parser.add_argument("--output", default=str(ARCHIVE_ROOT / "index.json"))
    parser.add_argument(
        "--viewer-output",
        default=str(VIEWER_DATA_JS),
        help="Write a JS data mirror for analysis_project/index.html. Use empty string to skip.",
    )
    return parser.parse_args()


def main() -> None:
    from osint_core.utils import utc_now_iso

    args = parse_args()
    index = build_index()
    index["generated_at"] = utc_now_iso()
    write_json(Path(args.output), index)
    if args.viewer_output:
        write_viewer_data(Path(args.viewer_output), index)
    print(f"indexed {index['article_count']} article(s): {args.output}")


if __name__ == "__main__":
    main()
