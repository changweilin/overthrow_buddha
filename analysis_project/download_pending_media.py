from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from osint_core.storage import read_metadata, write_metadata
from osint_core.utils import ARTICLES_ROOT, ensure_dir, sha256_bytes, utc_now_iso


USER_AGENT = "OverthrowBuddhaOSINTCrawler/1.0 (public OSINT media follow-up)"


def extension_for(url: str, content_type: str) -> str:
    path = urlparse(url).path.lower()
    for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".mp4", ".webm", ".mov"]:
        if path.endswith(ext):
            return ext
    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    if "gif" in content_type:
        return ".gif"
    if "svg" in content_type:
        return ".svg"
    if "video" in content_type:
        return ".mp4"
    return ".jpg"


def fetch_limited(url: str, max_bytes: int) -> tuple[dict[str, str], bytes]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urlopen(request, timeout=30) as response:
        headers = dict(response.headers.items())
        body = response.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise ValueError(f"media exceeds max size of {max_bytes} bytes")
    return headers, body


def process_folder(folder: Path, include_videos: bool, max_bytes: int, dry_run: bool) -> int:
    metadata = read_metadata(folder)
    if not metadata:
        return 0
    media = metadata.setdefault("media", {})
    changed = 0
    ensure_dir(folder / "media")

    for index, image in enumerate(media.get("images", []), start=1):
        if image.get("status") != "pending_download" or not image.get("url"):
            continue
        if dry_run:
            print(f"[dry-run] image pending: {image['url']}")
            changed += 1
            continue
        try:
            headers, body = fetch_limited(image["url"], max_bytes)
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            image["error"] = str(exc)
            continue
        digest = sha256_bytes(body)
        filename = f"image-pending-{index:02d}-{digest[:10]}{extension_for(image['url'], headers.get('Content-Type', ''))}"
        target = folder / "media" / filename
        target.write_bytes(body)
        image.update(
            {
                "status": "downloaded",
                "path": f"media/{filename}",
                "size_bytes": len(body),
                "sha256": digest,
                "content_type": headers.get("Content-Type", ""),
            }
        )
        changed += 1

    if include_videos:
        for index, video in enumerate(media.get("videos", []), start=1):
            if video.get("status") != "pending_download" or not video.get("url"):
                continue
            if dry_run:
                print(f"[dry-run] video pending: {video['url']}")
                changed += 1
                continue
            try:
                headers, body = fetch_limited(video["url"], max_bytes)
            except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                video["error"] = str(exc)
                continue
            digest = sha256_bytes(body)
            filename = f"video-pending-{index:02d}-{digest[:10]}{extension_for(video['url'], headers.get('Content-Type', ''))}"
            target = folder / "media" / filename
            target.write_bytes(body)
            video.update(
                {
                    "status": "downloaded",
                    "path": f"media/{filename}",
                    "size_bytes": len(body),
                    "sha256": digest,
                    "content_type": headers.get("Content-Type", ""),
                }
            )
            changed += 1

    if changed and not dry_run:
        metadata["media_updated_at"] = utc_now_iso()
        write_metadata(folder, metadata)
    return changed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download media previously marked pending_download")
    parser.add_argument("--include-videos", action="store_true", help="Also download videos marked pending_download")
    parser.add_argument("--max-mb", type=int, default=10, help="Maximum bytes per media item in MiB")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    max_bytes = args.max_mb * 1024 * 1024
    total = 0
    if ARTICLES_ROOT.exists():
        for metadata_path in ARTICLES_ROOT.glob("*/*/metadata.json"):
            total += process_folder(metadata_path.parent, args.include_videos, max_bytes, args.dry_run)
    print(f"processed {total} pending media item(s)")


if __name__ == "__main__":
    main()

