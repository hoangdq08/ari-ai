from __future__ import annotations

import re
import unicodedata
from collections import Counter


NOISE_PATTERN = re.compile(r"[^\w\s.,;:!?%()/\-+À-ỹĐđ]", re.UNICODE)
STOP_SECTION_PATTERNS = [
    re.compile(r"^bài viết (trước|tiếp theo)", re.IGNORECASE),
    re.compile(r"^sản phẩm nổi bật", re.IGNORECASE),
    re.compile(r"^danh mục sản phẩm", re.IGNORECASE),
    re.compile(r"^xem sản phẩm", re.IGNORECASE),
    re.compile(r"^siêu thị làm vườn", re.IGNORECASE),
    re.compile(r"^cảm ơn (các bạn|bạn)", re.IGNORECASE),
    re.compile(r"^greenhome\s+giải pháp", re.IGNORECASE),
    re.compile(r"^an tín nông là", re.IGNORECASE),
    re.compile(r"^an tín nông cung cấp", re.IGNORECASE),
    re.compile(r"^antinnong là", re.IGNORECASE),
    re.compile(r"^với mong muốn đồng hành", re.IGNORECASE),
]
DROP_LINE_PATTERNS = [
    re.compile(r"^blog làm vườn", re.IGNORECASE),
    re.compile(r"^mẹo hay cần biết", re.IGNORECASE),
    re.compile(r"^trở về$", re.IGNORECASE),
    re.compile(r"^share$", re.IGNORECASE),
    re.compile(r"^tweet$", re.IGNORECASE),
    re.compile(r"^toggle$", re.IGNORECASE),
    re.compile(r"^mục lục$", re.IGNORECASE),
    re.compile(r"^không có từ khóa$", re.IGNORECASE),
    re.compile(r"^\d+/\d+\s*-", re.IGNORECASE),
    re.compile(r"^hotline:", re.IGNORECASE),
    re.compile(r"^email:", re.IGNORECASE),
    re.compile(r"^website:", re.IGNORECASE),
    re.compile(r"^địa chỉ:", re.IGNORECASE),
    # --- PDF front-matter / TOC / author-list noise ---
    re.compile(r"\.{4,}"),                                        # TOC dotted leaders
    re.compile(r"^\d+\.\d+\.\d*\s"),                              # section numbers "1.4.1. Yêu cầu"
    re.compile(r"^(ThS|TS|PGS|GS|CN|KS)\.\s", re.IGNORECASE),    # academic title at start
    re.compile(r"^\d+\s*[-–.]\s*(ThS|TS|PGS|GS|CN|KS)\b", re.IGNORECASE),  # "4. ThS. Hoàng..."
    re.compile(r"[-–]\s*(GIZ|WASI|IPSARD|FAO|UNDP|JICA)\b"),     # org affiliation
    re.compile(r"(Viện trưởng|Phó Viện trưởng)\s+(WASI|IPSARD|VAAS|NOMAFSI)\b", re.IGNORECASE),
    re.compile(r"^trang\s+\d+", re.IGNORECASE),                   # "Trang 15"
]


def clean_text(raw_text: str) -> str:
    text = unicodedata.normalize("NFC", raw_text)
    text = text.replace("\ufeff", " ").replace("\u00a0", " ")
    text = _remove_repeated_headers_footers(text)
    text = NOISE_PATTERN.sub(" ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = _merge_broken_lines(text)
    text = _drop_low_value_lines(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _remove_repeated_headers_footers(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    normalized = [re.sub(r"\d+", "#", line.lower()) for line in lines if 5 <= len(line) <= 120]
    repeated = {line for line, count in Counter(normalized).items() if count >= 3}
    kept = []
    for original in lines:
        key = re.sub(r"\d+", "#", original.strip().lower())
        if key not in repeated:
            kept.append(original)
    return "\n".join(kept)


def _merge_broken_lines(text: str) -> str:
    merged: list[str] = []
    buffer = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if buffer:
                merged.append(buffer.strip())
                buffer = ""
            merged.append("")
            continue
        if buffer and not buffer.endswith((".", ":", ";", "?", "!", ")")) and line[:1].islower():
            buffer = f"{buffer} {line}"
        else:
            if buffer:
                merged.append(buffer.strip())
            buffer = line
    if buffer:
        merged.append(buffer.strip())
    return "\n".join(merged)


def _drop_low_value_lines(text: str) -> str:
    kept = []
    seen_recent: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            kept.append("")
            continue
        if any(pattern.search(stripped) for pattern in STOP_SECTION_PATTERNS):
            break
        if any(pattern.search(stripped) for pattern in DROP_LINE_PATTERNS):
            continue
        if len(stripped) < 18:
            continue
        if re.fullmatch(r"[\d\s./-]+", stripped):
            continue
        if stripped.lower() in {"mục lục", "tài liệu tham khảo", "phụ lục"}:
            continue
        key = re.sub(r"\s+", " ", stripped.lower())
        if key in seen_recent:
            continue
        seen_recent = (seen_recent + [key])[-12:]
        kept.append(stripped)
    return "\n".join(kept)
