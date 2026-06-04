from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .data_ingestion import DataIngestor, IngestedDocument
from .source_policy import infer_reliability


BLOCKED_HOST_TOKENS = {
    "twitter.com",
    "x.com",
    "linkedin.com",
    "pinterest.com",
    "tiktok.com",
    "zalo.me",
    "maps.app.goo.gl",
    "goo.gl",
    "online.gov.vn",
    "dmca.com",
}
SOCIAL_RESEARCH_HOST_TOKENS = {
    "facebook.com",
    "youtube.com",
    "youtu.be",
}
BLOCKED_PATH_TOKENS = {
    "user",
    "login",
    "register",
    "tai-khoan",
    "lost-password",
    "my-account",
    "cart",
    "gio-hang",
    "checkout",
    "shop",
    "cua-hang",
    "product",
    "product-category",
    "danh-muc",
    "category",
    "tag",
    "author",
    "lien-he",
    "contact",
    "gioi-thieu",
    "about",
    "chinh-sach",
    "privacy",
    "terms",
    "bao-hanh",
    "van-chuyen",
    "thanh-toan",
    "share",
    "sharer",
    "pin",
    "search",
    "may-pha",
    "may-xay",
    "linh-kien",
    "phu-kien",
    "barista",
    "secondhand",
    "da-qua-su-dung",
    "ban-dong",
    "cho-thue",
}
AGRI_URL_SIGNALS = {
    "ca-phe",
    "caphe",
    "coffee",
    "benh",
    "giong",
    "gi-sat",
    "ri-sat",
    "than-thu",
    "dom-mat-cua",
    "cercospora",
    "anthracnose",
    "khuyen-nong",
    "nong-nghiep",
    "ky-thuat",
    "quy-trinh",
    "bon-phan",
    "phan-bon",
    "sau-benh",
    "benh-hai",
    "cay-trong",
    "cay-ca-phe",
    "pdf",
    "tailieu",
    "tai-lieu",
}


@dataclass
class CrawlItem:
    url: str
    status: str
    source_id: str | None = None
    title: str | None = None
    source_type: str | None = None
    reliability_level: str = "internet"
    content_type: str | None = None
    error: str | None = None
    discovered_links: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class InternetCrawler:
    def __init__(self, ingestor: DataIngestor, candidate_dir: str | Path):
        self.ingestor = ingestor
        self.candidate_dir = Path(candidate_dir)
        self.candidate_dir.mkdir(parents=True, exist_ok=True)
        self.history_path = self.candidate_dir / "crawl_history.jsonl"
        self.links_path = self.candidate_dir / "discovered_links.jsonl"

    def crawl_urls(
        self,
        urls: list[str],
        reliability_level: str = "internet",
        max_pages: int = 10,
        collect_links: bool = False,
        same_domain_only: bool = True,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> list[CrawlItem]:
        queue = list(dict.fromkeys(urls))[:max_pages]
        seen: set[str] = set()
        results: list[CrawlItem] = []
        seed_domains = {urlparse(url).netloc for url in urls}

        while queue and len(seen) < max_pages:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            if progress_callback:
                progress_callback({"event": "fetching", "url": url, "seen": len(seen), "max_pages": max_pages})
            item = self._crawl_one(url, reliability_level, collect_links=collect_links)
            results.append(item)
            self._append_jsonl(self.history_path, item.to_dict())
            if progress_callback:
                progress_callback(
                    {
                        "event": item.status,
                        "url": item.url,
                        "source_id": item.source_id,
                        "title": item.title,
                        "source_type": item.source_type,
                        "error": item.error,
                        "discovered_link_count": len(item.discovered_links or []),
                    }
                )

            if collect_links and item.discovered_links:
                for link in item.discovered_links:
                    parsed = urlparse(link)
                    if parsed.scheme not in {"http", "https"}:
                        continue
                    if same_domain_only and parsed.netloc not in seed_domains:
                        self._append_jsonl(self.links_path, {"url": link, "status": "candidate_external", "found_from": url})
                        continue
                    self._append_jsonl(self.links_path, {"url": link, "status": "queued_or_seen", "found_from": url})
                    if link not in seen and link not in queue and len(queue) + len(seen) < max_pages:
                        queue.append(link)
        return results

    def recent_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._read_jsonl_tail(self.history_path, limit)

    def recent_links(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._read_jsonl_tail(self.links_path, limit)

    def _crawl_one(self, url: str, reliability_level: str, collect_links: bool) -> CrawlItem:
        effective_reliability = infer_reliability(url, reliability_level)
        try:
            response = requests.get(url, timeout=20, headers={"User-Agent": "NongTriAI/0.1 internet crawler"})
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            title, links = self._extract_title_and_links(url, response.text, content_type, collect_links)
            ingested: IngestedDocument = self.ingestor.ingest_url(url, title, effective_reliability)
            status = "duplicate" if ingested.is_duplicate else "ingested"
            return CrawlItem(
                url=url,
                status=status,
                source_id=ingested.source_id,
                title=ingested.metadata.get("title"),
                source_type=ingested.metadata.get("source_type"),
                reliability_level=effective_reliability,
                content_type=content_type,
                discovered_links=links,
            )
        except Exception as exc:
            item = CrawlItem(url=url, status="failed", reliability_level=effective_reliability, error=str(exc), discovered_links=[])
            return item

    def _extract_title_and_links(self, url: str, text: str, content_type: str, collect_links: bool) -> tuple[str | None, list[str]]:
        if "html" not in content_type.lower():
            return None, []
        soup = BeautifulSoup(text, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else None
        if not collect_links:
            return title, []

        links = []
        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href")
            absolute = urljoin(url, href)
            filtered = _normalize_discovered_link(absolute)
            if filtered and _is_relevant_discovered_link(filtered):
                links.append(filtered)
        return title, sorted(set(links))[:25]

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        payload = {"logged_at": datetime.now(timezone.utc).isoformat(), **payload}
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _read_jsonl_tail(self, path: Path, limit: int) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
        return [json.loads(line) for line in lines if line.strip()]


def _normalize_discovered_link(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return ""
    clean = parsed._replace(fragment="", query="").geturl()
    return unquote(clean).rstrip("/")


def _is_relevant_discovered_link(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower().strip("/")
    haystack = f"{host}/{path}"

    if any(token in host for token in BLOCKED_HOST_TOKENS):
        return False
    if any(token in host for token in SOCIAL_RESEARCH_HOST_TOKENS):
        return _is_relevant_social_research_link(host, path)
    if any(part in BLOCKED_PATH_TOKENS for part in path.split("/") if part):
        return False
    if any(token in haystack for token in BLOCKED_PATH_TOKENS):
        return False
    if Path(parsed.path).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".css", ".js"}:
        return False
    return any(signal in haystack for signal in AGRI_URL_SIGNALS)


def _is_relevant_social_research_link(host: str, path: str) -> bool:
    if any(token in path for token in {"sharer", "share.php", "sharearticle", "intent", "dialog", "plugins"}):
        return False
    if "facebook.com" in host:
        blocked_parts = {"login", "sharer.php", "share.php", "plugins", "privacy", "help", "marketplace", "groups_browse"}
        if any(part in blocked_parts for part in path.split("/") if part):
            return False
        return bool(path)
    if "youtube.com" in host:
        return path.startswith(("watch", "shorts/", "playlist", "channel/", "c/", "@"))
    if "youtu.be" in host:
        return bool(path)
    return False
