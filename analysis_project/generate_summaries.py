from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from osint_core.storage import read_metadata, write_metadata
from osint_core.utils import ARTICLES_ROOT, clean_text, load_env_file, utc_now_iso


def iter_article_folders() -> list[Path]:
    if not ARTICLES_ROOT.exists():
        return []
    return sorted(path.parent for path in ARTICLES_ROOT.glob("*/*/metadata.json"))


def load_gemini_model() -> Any | None:
    load_env_file()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        return None
    try:
        import google.generativeai as genai  # type: ignore
    except Exception:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-pro"))


def needs_summary(folder: Path, metadata: dict[str, Any]) -> bool:
    summary_path = folder / "summary.zh.md"
    if not summary_path.exists():
        return True
    return metadata.get("summary_status") in {"needs_update", "pending_model", "error"}


def read_original_text(folder: Path) -> str:
    path = folder / "original.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def build_prompt(metadata: dict[str, Any], original_markdown: str) -> str:
    safety_note = (
        "這些內容僅用於整理公開來源資訊。請避免提供操作性攻擊、規避偵測、武器製作、"
        "入侵、破壞或其他可能造成傷害的逐步流程。可整理高層次背景、政策、技術趨勢、"
        "風險觀察與公開事實。"
    )
    return f"""
請用繁體中文為以下公開來源文章製作 OSINT 閱讀摘要，輸出 Markdown。

請包含：
1. 3-5 點重點摘要
2. 文章涉及的主要行動者或組織
3. 高層次技術、政策或戰略意涵
4. 可持續追蹤的關鍵字
5. restricted_detail: true/false

安全要求：{safety_note}

標題：{metadata.get("title")}
來源：{metadata.get("source")}
URL：{metadata.get("url")}
restricted_detail：{metadata.get("restricted_detail")}

原文：
{original_markdown[:6000]}
"""


def fallback_pending_summary(metadata: dict[str, Any]) -> str:
    restricted = str(bool(metadata.get("restricted_detail"))).lower()
    return "\n".join(
        [
            f"# {metadata.get('title', 'Untitled')} - 摘要待產生",
            "",
            "> 目前尚未偵測到可用的 `GEMINI_API_KEY` 或 Gemini Python 套件，因此先保留待產生狀態。",
            "",
            f"- 來源：{metadata.get('source')}",
            f"- URL：{metadata.get('url')}",
            f"- restricted_detail：`{restricted}`",
            "",
            "## 摘要說明",
            "",
            "此專案僅保留公開 OSINT 的高層次背景、政策、技術趨勢與戰場觀察；若來源含可操作細節，正式摘要階段不得重述步驟、參數或攻擊流程。",
            "",
        ]
    )


def generate_summary(folder: Path, model: Any | None, force: bool) -> None:
    metadata = read_metadata(folder)
    if not metadata:
        return
    if not force and not needs_summary(folder, metadata):
        return

    original_markdown = read_original_text(folder)
    if not original_markdown:
        return

    if model is None:
        (folder / "summary.zh.md").write_text(fallback_pending_summary(metadata), encoding="utf-8")
        metadata["summary_status"] = "pending_model"
        metadata["summary_updated_at"] = utc_now_iso()
        write_metadata(folder, metadata)
        print(f"pending summary: {folder}")
        return

    prompt = build_prompt(metadata, original_markdown)
    try:
        response = model.generate_content(prompt)
        text = clean_text(getattr(response, "text", "") or "")
    except Exception as exc:
        text = ""
        metadata["summary_error"] = str(exc)

    if not text:
        (folder / "summary.zh.md").write_text(fallback_pending_summary(metadata), encoding="utf-8")
        metadata["summary_status"] = "pending_model"
    else:
        (folder / "summary.zh.md").write_text(text + "\n", encoding="utf-8")
        metadata["summary_status"] = "current"
        metadata.pop("summary_error", None)
    metadata["summary_updated_at"] = utc_now_iso()
    write_metadata(folder, metadata)
    print(f"summary updated: {folder}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Traditional Chinese OSINT summaries")
    parser.add_argument("--force", action="store_true", help="Regenerate all summaries")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = load_gemini_model()
    for folder in iter_article_folders():
        generate_summary(folder, model, args.force)


if __name__ == "__main__":
    main()
