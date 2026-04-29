from __future__ import annotations

import argparse
import logging
import random
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from osint_core.config import load_sources
from osint_core.html_extract import discover_article_links, extract_article
from osint_core.storage import article_folder, find_article_by_url, read_metadata, write_metadata
from osint_core.utils import (
    ARCHIVE_ROOT,
    clean_text,
    ensure_dir,
    looks_restricted_detail,
    sha256_bytes,
    sha256_text,
    slugify,
    utc_now_iso,
)


CONFIG_PATH = PROJECT_ROOT / "crawler_project" / "config" / "sources.yaml"
LOG_DIR = PROJECT_ROOT / "crawler_project" / "logs"
DEFAULT_USER_AGENT = "OverthrowBuddhaOSINTCrawler/1.0 (public OSINT; respectful rate limits)"


class RespectfulCrawler:
    def __init__(
        self,
        *,
        dry_run: bool = False,
        no_delay: bool = False,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.dry_run = dry_run
        self.no_delay = no_delay
        self.user_agent = user_agent
        self.robots_cache: dict[str, RobotFileParser] = {}
        self.last_domain_access: dict[str, float] = {}

    def fetch(
        self,
        url: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
        accept: str = "text/html,application/xhtml+xml",
    ) -> tuple[int, dict[str, str], bytes]:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": accept,
        }
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=30) as response:
                return response.status, dict(response.headers.items()), response.read()
        except HTTPError as error:
            if error.code == 304:
                return 304, dict(error.headers.items()), b""
            raise

    def robots_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        parser = self.robots_cache.get(robots_url)
        if parser is None:
            parser = RobotFileParser()
            parser.set_url(robots_url)
            try:
                parser.read()
            except Exception as exc:
                logging.warning("Could not read robots.txt for %s: %s", parsed.netloc, exc)
            self.robots_cache[robots_url] = parser
        return parser.can_fetch(self.user_agent, url)

    def polite_wait(self, source: dict[str, Any], url: str) -> None:
        if self.no_delay or self.dry_run:
            return
        domain = urlparse(url).netloc.lower()
        delay_cfg = source.get("delay_seconds", {}) if isinstance(source.get("delay_seconds"), dict) else {}
        min_delay = float(delay_cfg.get("min", 8))
        max_delay = float(delay_cfg.get("max", 20))
        delay = random.uniform(min_delay, max(max_delay, min_delay))

        elapsed = time.time() - self.last_domain_access.get(domain, 0)
        wait_for = max(0.0, delay - elapsed)
        if wait_for:
            logging.info("Waiting %.1fs before reading next page on %s", wait_for, domain)
            time.sleep(wait_for)
        self.last_domain_access[domain] = time.time()

    def run(self, source_filter: str | None, limit_override: int | None) -> None:
        ensure_dir(ARCHIVE_ROOT)
        sources = load_sources(CONFIG_PATH)
        selected = [
            source
            for source in sources
            if not source_filter or source.get("name", "").lower() == source_filter.lower()
        ]
        if source_filter and not selected:
            raise SystemExit(f"No source named {source_filter!r} found in {CONFIG_PATH}")

        for source in selected:
            self.process_source(source, limit_override)

    def process_source(self, source: dict[str, Any], limit_override: int | None) -> None:
        source_url = str(source["url"])
        source_name = str(source["name"])
        limit = self.resolve_limit(source, limit_override)
        logging.info("Scanning source: %s", source_name)
        if not self.robots_allowed(source_url):
            logging.warning("robots.txt disallows source page: %s", source_url)
            return

        try:
            status, _headers, body = self.fetch(source_url)
        except (HTTPError, URLError, TimeoutError) as exc:
            logging.error("Failed to fetch source %s: %s", source_url, exc)
            return
        if status >= 400:
            logging.error("Source returned HTTP %s: %s", status, source_url)
            return

        html_text = body.decode("utf-8", errors="replace")
        if str(source.get("type", "html")).lower() == "rss":
            links = self.apply_limit(self.discover_rss_links(html_text, source), limit)
        else:
            links = self.apply_limit(
                discover_article_links(
                    html_text,
                    source_url,
                    source.get("allowed_domains", []),
                    source.get("include_url_keywords", []),
                ),
                limit,
            )
        logging.info("Discovered %s candidate article(s)", len(links))
        if self.dry_run:
            for link in links:
                logging.info("[dry-run] would process %s", link)
            return

        for link in links:
            self.polite_wait(source, link)
            self.process_article(source, link)

    @staticmethod
    def resolve_limit(source: dict[str, Any], limit_override: int | None) -> int | None:
        raw_limit = limit_override if limit_override is not None else source.get("limit")
        if raw_limit in {None, "", "none", "None", "all", "All", 0, "0"}:
            return None
        return max(0, int(raw_limit))

    @staticmethod
    def apply_limit(links: list[str], limit: int | None) -> list[str]:
        if limit is None:
            return links
        return links[:limit]

    @staticmethod
    def discover_rss_links(xml_text: str, source: dict[str, Any]) -> list[str]:
        allowed = {domain.lower() for domain in source.get("allowed_domains", [])}
        keywords = [keyword.lower() for keyword in source.get("include_url_keywords", [])]
        links: list[str] = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            logging.error("Source is configured as RSS but did not return valid XML: %s", source.get("url"))
            return links

        for item in root.findall(".//item"):
            link = (item.findtext("link") or "").strip()
            if not link:
                continue
            parsed = urlparse(link)
            if allowed and parsed.netloc.lower() not in allowed:
                continue
            item_text = " ".join(
                [
                    link,
                    item.findtext("title") or "",
                    item.findtext("description") or "",
                    item.findtext("category") or "",
                ]
            ).lower()
            if keywords and not any(keyword in item_text for keyword in keywords):
                continue
            links.append(link)
        return links

    def process_article(self, source: dict[str, Any], url: str) -> None:
        if not self.robots_allowed(url):
            logging.warning("robots.txt disallows article: %s", url)
            return

        old_folder = find_article_by_url(url)
        old_metadata = read_metadata(old_folder) if old_folder else {}
        try:
            status, headers, body = self.fetch(
                url,
                etag=old_metadata.get("etag"),
                last_modified=old_metadata.get("last_modified"),
            )
        except HTTPError as exc:
            if exc.code in {403, 429}:
                logging.warning("Backoff requested by server for %s: HTTP %s", url, exc.code)
                time.sleep(60 if not self.no_delay else 0)
                return
            logging.error("HTTP error for %s: %s", url, exc)
            return
        except (URLError, TimeoutError) as exc:
            logging.error("Network error for %s: %s", url, exc)
            return

        if status == 304 and old_folder:
            old_metadata["last_seen"] = utc_now_iso()
            write_metadata(old_folder, old_metadata)
            logging.info("Unchanged via conditional request: %s", url)
            return

        html_text = body.decode("utf-8", errors="replace")
        extracted = extract_article(html_text, url)
        content_hash = sha256_text(clean_text(extracted.text))

        if old_folder and old_metadata.get("content_hash") == content_hash:
            old_metadata.update(
                {
                    "last_seen": utc_now_iso(),
                    "etag": headers.get("ETag") or old_metadata.get("etag"),
                    "last_modified": headers.get("Last-Modified") or old_metadata.get("last_modified"),
                }
            )
            write_metadata(old_folder, old_metadata)
            logging.info("Unchanged via content hash: %s", url)
            return

        folder = old_folder or article_folder(str(source["name"]), extracted.title, url)
        ensure_dir(folder / "media")
        restricted = looks_restricted_detail(extracted.text)
        images = self.handle_images(source, extracted.images, folder)
        videos = extracted.videos
        now = utc_now_iso()
        metadata = {
            "url": url,
            "title": extracted.title,
            "source": source["name"],
            "source_url": source["url"],
            "collected_at": old_metadata.get("collected_at", now),
            "updated_at": now,
            "last_seen": now,
            "etag": headers.get("ETag") or old_metadata.get("etag"),
            "last_modified": headers.get("Last-Modified") or old_metadata.get("last_modified"),
            "content_hash": content_hash,
            "restricted_detail": restricted,
            "summary_status": "needs_update",
            "media": {
                "images": images,
                "videos": videos,
            },
        }
        self.write_original(folder, metadata, extracted.text, extracted.description)
        write_metadata(folder, metadata)
        logging.info("Saved article: %s", folder)

    def handle_images(
        self,
        source: dict[str, Any],
        images: list[dict[str, str]],
        folder: Path,
    ) -> list[dict[str, Any]]:
        media_cfg = source.get("media", {}) if isinstance(source.get("media"), dict) else {}
        image_mode = media_cfg.get("images", "download")
        results: list[dict[str, Any]] = []
        for index, image in enumerate(images[:10], start=1):
            item: dict[str, Any] = dict(image)
            if image_mode != "download":
                item["status"] = "linked_only"
                results.append(item)
                continue
            try:
                status, headers, body = self.fetch(
                    image["url"],
                    accept="image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                )
            except Exception as exc:
                item["status"] = "pending_download"
                item["error"] = str(exc)
                results.append(item)
                continue
            if status >= 400 or not body:
                item["status"] = "pending_download"
                item["http_status"] = status
                results.append(item)
                continue
            extension = self.extension_for_image(image["url"], headers.get("Content-Type", ""))
            filename = f"image-{index:02d}-{sha256_bytes(body)[:10]}{extension}"
            target = folder / "media" / filename
            target.write_bytes(body)
            item.update(
                {
                    "status": "downloaded",
                    "path": f"media/{filename}",
                    "size_bytes": len(body),
                    "sha256": sha256_bytes(body),
                    "content_type": headers.get("Content-Type", ""),
                }
            )
            results.append(item)
        return results

    @staticmethod
    def extension_for_image(url: str, content_type: str) -> str:
        path = urlparse(url).path.lower()
        for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"]:
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
        return ".jpg"

    @staticmethod
    def write_original(folder: Path, metadata: dict[str, Any], text: str, description: str) -> None:
        display_text = text
        if metadata.get("restricted_detail"):
            display_text = (
                "This source appears to contain operationally actionable details. "
                "The local archive keeps only high-level OSINT context for safety.\n\n"
                f"{description or text[:1200]}"
            )

        lines = [
            f"# {metadata['title']}",
            "",
            f"- Source: {metadata['source']}",
            f"- URL: {metadata['url']}",
            f"- Collected at: {metadata['collected_at']}",
            f"- Updated at: {metadata['updated_at']}",
            f"- Content hash: `{metadata['content_hash']}`",
            f"- Restricted detail: `{str(metadata['restricted_detail']).lower()}`",
            "",
            "## Media",
            "",
        ]
        for image in metadata["media"]["images"]:
            if image.get("status") == "downloaded" and image.get("path"):
                alt = image.get("alt") or "Source image"
                lines.append(f"![{alt}]({image['path']})")
            else:
                lines.append(f"- Image: {image.get('url')} ({image.get('status')})")
        for video in metadata["media"]["videos"]:
            lines.append(f"- Video: {video.get('url')} ({video.get('status', 'linked_only')})")
        lines.extend(["", "## Text", "", display_text.strip(), ""])
        (folder / "original.md").write_text("\n".join(lines), encoding="utf-8")


def configure_logging() -> None:
    ensure_dir(LOG_DIR)
    log_path = LOG_DIR / f"crawler-{datetime.now().strftime('%Y%m%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Incremental public OSINT crawler")
    parser.add_argument("--source", help="Run a single source by exact configured name")
    parser.add_argument("--limit", type=int, help="Override per-source article limit")
    parser.add_argument("--dry-run", action="store_true", help="Discover work without writing archive files")
    parser.add_argument("--no-delay", action="store_true", help="Skip polite waits for local validation")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging()
    crawler = RespectfulCrawler(dry_run=args.dry_run, no_delay=args.no_delay)
    crawler.run(args.source, args.limit)


if __name__ == "__main__":
    main()
