from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin, urlparse

from .utils import canonical_url, clean_text


@dataclass
class ExtractedArticle:
    title: str
    text: str
    description: str
    links: list[str] = field(default_factory=list)
    images: list[dict[str, str]] = field(default_factory=list)
    videos: list[dict[str, str]] = field(default_factory=list)


class ArticleHTMLParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.links: list[str] = []
        self.images: list[dict[str, str]] = []
        self.videos: list[dict[str, str]] = []
        self.description = ""
        self._tag_stack: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key.lower(): value or "" for key, value in attrs}
        self._tag_stack.append(tag)
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "meta":
            name = attr.get("name", "").lower() or attr.get("property", "").lower()
            if name in {"description", "og:description"} and attr.get("content"):
                self.description = clean_text(attr["content"])
        if tag == "a" and attr.get("href"):
            self.links.append(urljoin(self.base_url, attr["href"]))
        if tag == "img":
            src = attr.get("src") or attr.get("data-src") or attr.get("data-original")
            if src:
                self.images.append(
                    {
                        "url": urljoin(self.base_url, src),
                        "alt": clean_text(attr.get("alt", "")),
                        "status": "pending_download",
                    }
                )
        if tag in {"video", "iframe"}:
            src = attr.get("src")
            if src:
                self.videos.append(
                    {
                        "url": urljoin(self.base_url, src),
                        "title": clean_text(attr.get("title", "")),
                        "description": "",
                        "status": "linked_only",
                    }
                )

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = clean_text(data)
        if not text:
            return
        if self._tag_stack and self._tag_stack[-1] == "title":
            self.title_parts.append(text)
            return
        if any(tag in self._tag_stack for tag in {"article", "main", "p", "h1", "h2", "li"}):
            self.text_parts.append(text)


def extract_article(html_text: str, base_url: str) -> ExtractedArticle:
    parser = ArticleHTMLParser(base_url)
    parser.feed(html_text)
    title = clean_text(" ".join(parser.title_parts))
    text = clean_text("\n\n".join(parser.text_parts))
    if not title:
        h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, flags=re.I | re.S)
        if h1_match:
            title = clean_text(re.sub(r"<[^>]+>", " ", html.unescape(h1_match.group(1))))
    if not title:
        title = urlparse(base_url).path.rstrip("/").split("/")[-1].replace("-", " ").title() or "Untitled"
    return ExtractedArticle(
        title=title,
        text=text,
        description=parser.description,
        links=_dedupe_urls(parser.links),
        images=_dedupe_media(parser.images),
        videos=_dedupe_media(parser.videos),
    )


def discover_article_links(
    html_text: str,
    base_url: str,
    allowed_domains: Iterable[str],
    include_keywords: Iterable[str],
) -> list[str]:
    article = extract_article(html_text, base_url)
    allowed = {domain.lower() for domain in allowed_domains}
    keywords = [keyword.lower() for keyword in include_keywords]
    results: list[str] = []
    base_canonical = canonical_url(base_url)
    for link in article.links:
        if canonical_url(link) == base_canonical:
            continue
        parsed = urlparse(link)
        if allowed and parsed.netloc.lower() not in allowed:
            continue
        if keywords and not any(keyword in link.lower() for keyword in keywords):
            continue
        if parsed.scheme in {"http", "https"}:
            results.append(link)
    return _dedupe_urls(results)


def _dedupe_urls(urls: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for url in urls:
        cleaned = url.split("#", 1)[0]
        if cleaned in seen:
            continue
        seen.add(cleaned)
        deduped.append(cleaned)
    return deduped


def _dedupe_media(media_items: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for item in media_items:
        url = item.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(item)
    return deduped
