from __future__ import annotations

import json
import re
import unicodedata
import base64
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from .source_policy import infer_reliability, source_penalty


COFFEE_TERMS = {
    "cà phê",
    "ca phe",
    "coffee",
    "bệnh",
    "benh",
    "khuyến nông",
    "khuyen nong",
    "giống",
    "giong",
    "trs1",
    "tr4",
    "robusta",
    "arabica",
    "vối",
    "voi",
    "chè",
    "che",
    "năng suất",
    "nang suat",
    "canh tác",
    "canh tac",
    "tưới",
    "tuoi",
    "phân bón",
    "phan bon",
    "rệp",
    "rep",
    "tuyến trùng",
    "tuyen trung",
    "vàng lá",
    "vang la",
    "thối rễ",
    "thoi re",
    "tây nguyên",
    "tay nguyen",
    "hạn hán",
    "han han",
    "dinh dưỡng",
    "dinh duong",
    "chi phí",
    "chi phi",
    "kinh tế",
    "kinh te",
    "tạo tán",
    "tao tan",
    "tỉa cành",
    "tia canh",
    "tỉa cành",
    "nước tưới",
    "nuoc tuoi",
    "chống hạn",
    "chong han",
    "dư lượng",
    "du luong",
    "bảo vệ thực vật",
    "bao ve thuc vat",
    "xuất khẩu",
    "xuat khau",
    "ghép cải tạo",
    "ghep cai tao",
    "vườn già",
    "vuon gia",
    "tiêu chuẩn",
    "tieu chuan",
    "bao tiêu",
    "bao tieu",
    "vietgap",
    "4c",
    "rainforest",
    "organic",
}

COFFEE_ANCHOR_TERMS = {
    "cà phê",
    "ca phe",
    "coffee",
    "trs1",
    "tr4",
    "robusta",
    "arabica",
    "eakmat",
    "tây nguyên",
    "tay nguyen",
}

OFF_TOPIC_TERMS = {
    "remote jobs",
    "freelance jobs",
    "từ vựng tiếng anh",
    "vocabulary",
    "tranh chấp môi trường",
    "luật môi trường",
    "chứng khoán",
    "solidworks",
    "mặt trận tổ quốc",
    "kỹ thuật xây dựng",
}


@dataclass
class SearchCandidate:
    title: str
    url: str
    snippet: str
    source_type: str
    reliability_level: str
    relevance_score: float
    status: str = "candidate"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SearchDiscovery:
    def __init__(self, candidate_dir: str | Path):
        self.candidate_dir = Path(candidate_dir)
        self.candidate_dir.mkdir(parents=True, exist_ok=True)
        self.history_path = self.candidate_dir / "search_candidates.jsonl"

    def search(self, query: str, max_results: int = 10) -> list[SearchCandidate]:
        candidates: list[SearchCandidate] = []
        try:
            candidates = self._duckduckgo_search(query, max_results=max_results)
        except requests.RequestException:
            candidates = []
        if not candidates:
            try:
                candidates = self._bing_search(query, max_results=max_results)
            except requests.RequestException:
                candidates = []
        if not candidates:
            candidates = self._cached_search(query, max_results=max_results)
        for candidate in candidates:
            self._append_jsonl(self.history_path, {"query": query, **candidate.to_dict()})
        return candidates

    def recent_candidates(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.history_path.exists():
            return []
        lines = self.history_path.read_text(encoding="utf-8").splitlines()[-limit:]
        return [json.loads(line) for line in lines if line.strip()]

    def _cached_search(self, query: str, max_results: int) -> list[SearchCandidate]:
        if not self.history_path.exists():
            return []

        rows: list[dict[str, Any]] = []
        for line in self.history_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        scored: dict[str, SearchCandidate] = {}
        for row in rows:
            title = row.get("title") or ""
            url = row.get("url") or ""
            snippet = row.get("snippet") or ""
            if not url:
                continue
            reliability = row.get("reliability_level") or _reliability(url)
            source_type = row.get("source_type") or _source_type(url)
            score = _score_candidate(query, title, snippet, url, reliability)
            if not _is_relevant_candidate(query, title, snippet, url, score):
                continue
            candidate = SearchCandidate(
                title=title,
                url=url,
                snippet=snippet,
                source_type=source_type,
                reliability_level=reliability,
                relevance_score=score,
                status="cached_candidate",
            )
            previous = scored.get(url)
            if not previous or candidate.relevance_score > previous.relevance_score:
                scored[url] = candidate

        return sorted(scored.values(), key=lambda item: item.relevance_score, reverse=True)[:max_results]

    def _duckduckgo_search(self, query: str, max_results: int) -> list[SearchCandidate]:
        candidates: list[SearchCandidate] = []
        seen: set[str] = set()
        session = requests.Session()
        payload: dict[str, str] | None = {"q": query}
        page_count = 0

        while payload and len(candidates) < max_results and page_count < 10:
            response = session.post(
                "https://html.duckduckgo.com/html/",
                data=payload,
                timeout=25,
                headers={"User-Agent": "NongTriAI/0.1 search discovery"},
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            page_count += 1

            for result in soup.select(".result"):
                link = result.select_one(".result__a")
                if not link:
                    continue
                url = _normalize_ddg_url(link.get("href") or "")
                if not url or url in seen:
                    continue
                seen.add(url)

                snippet_node = result.select_one(".result__snippet")
                title = link.get_text(" ", strip=True)
                snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
                source_type = _source_type(url)
                reliability = _reliability(url)
                score = _score_candidate(query, title, snippet, url, reliability)
                if not _is_relevant_candidate(query, title, snippet, url, score):
                    continue
                candidates.append(
                    SearchCandidate(
                        title=title,
                        url=url,
                        snippet=snippet,
                        source_type=source_type,
                        reliability_level=reliability,
                        relevance_score=score,
                    )
                )
                if len(candidates) >= max_results:
                    break

            payload = _next_page_payload(soup)

        return sorted(candidates, key=lambda item: item.relevance_score, reverse=True)

    def _bing_search(self, query: str, max_results: int) -> list[SearchCandidate]:
        response = requests.get(
            "https://www.bing.com/search",
            params={"q": query, "count": min(max_results, 50), "setlang": "vi"},
            timeout=25,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                )
            },
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        candidates: list[SearchCandidate] = []
        seen: set[str] = set()

        for result in soup.select("li.b_algo"):
            link = result.select_one("h2 a")
            if not link:
                continue
            url = _normalize_bing_url(link.get("href") or "")
            if not url or url in seen:
                continue
            seen.add(url)
            snippet_node = result.select_one(".b_caption p") or result.select_one("p")
            title = link.get_text(" ", strip=True)
            snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
            source_type = _source_type(url)
            reliability = _reliability(url)
            score = _score_candidate(query, title, snippet, url, reliability)
            if not _is_relevant_candidate(query, title, snippet, url, score):
                continue
            candidates.append(
                SearchCandidate(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source_type=source_type,
                    reliability_level=reliability,
                    relevance_score=score,
                )
            )
            if len(candidates) >= max_results:
                break

        return sorted(candidates, key=lambda item: item.relevance_score, reverse=True)

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        payload = {"logged_at": datetime.now(timezone.utc).isoformat(), **payload}
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _normalize_ddg_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("//duckduckgo.com/l/"):
        parsed = urlparse("https:" + url)
        uddg = parse_qs(parsed.query).get("uddg", [""])[0]
        return unquote(uddg)
    if "duckduckgo.com/l/" in url:
        parsed = urlparse(url)
        uddg = parse_qs(parsed.query).get("uddg", [""])[0]
        return unquote(uddg)
    return url


def _normalize_bing_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    if "bing.com" not in parsed.netloc or "/ck/a" not in parsed.path:
        return url
    encoded = parse_qs(parsed.query).get("u", [""])[0]
    if encoded.startswith("a1"):
        encoded = encoded[2:]
    if not encoded:
        return url
    padding = "=" * (-len(encoded) % 4)
    try:
        decoded = base64.urlsafe_b64decode((encoded + padding).encode("ascii")).decode("utf-8")
        return decoded if decoded.startswith(("http://", "https://")) else url
    except Exception:
        return url


def _next_page_payload(soup: BeautifulSoup) -> dict[str, str] | None:
    for form in soup.select("form"):
        inputs = form.select("input")
        if not any(item.get("value") == "Next" for item in inputs):
            continue
        payload: dict[str, str] = {}
        for item in inputs:
            name = item.get("name")
            if name:
                payload[name] = item.get("value") or ""
        payload.pop(None, None)
        return payload or None
    return None


def _source_type(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix == ".docx":
        return "docx"
    if suffix == ".txt":
        return "txt"
    return "web"


def _reliability(url: str) -> str:
    return infer_reliability(url, "internet")


def _score_candidate(query: str, title: str, snippet: str, url: str, reliability: str) -> float:
    haystack = _search_text(title, snippet, url)
    query_terms = _query_terms(query)
    query_hits = sum(1 for term in query_terms if term in haystack)
    coffee_hits = sum(1 for term in COFFEE_TERMS if term in haystack)
    reliability_bonus = {"official": 2.2, "semi_official": 1.1, "manual": 0.5, "internet": 0.0}.get(reliability, 0.0)
    type_bonus = 0.4 if _source_type(url) in {"pdf", "docx"} else 0.0
    penalty = source_penalty(title, url, snippet) * 2.0
    return round(max(0.0, query_hits * 0.8 + coffee_hits * 0.35 + reliability_bonus + type_bonus - penalty), 3)


def _search_text(title: str, snippet: str, url: str) -> str:
    text = f"{title} {snippet} {unquote(url)}".lower()
    return f"{text} {_strip_accents(text)}"


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").replace("đ", "d")


def _query_terms(query: str) -> set[str]:
    raw = query.lower()
    ascii_text = _strip_accents(raw)
    terms = {term for term in re.split(r"\W+", raw) if len(term) >= 3}
    terms.update(term for term in re.split(r"\W+", ascii_text) if len(term) >= 3)
    return terms


def _is_relevant_candidate(query: str, title: str, snippet: str, url: str, score: float) -> bool:
    haystack = _search_text(title, snippet, url)
    if any(term in haystack for term in OFF_TOPIC_TERMS):
        return False
    coffee_hits = sum(1 for term in COFFEE_ANCHOR_TERMS if term in haystack)
    query_hits = sum(1 for term in _query_terms(query) if term in haystack)
    if coffee_hits == 0:
        return False
    if source_penalty(title, url, snippet) >= 0.45 and score < 3.0:
        return False
    if score < 1.2 and query_hits < 1:
        return False
    return True
