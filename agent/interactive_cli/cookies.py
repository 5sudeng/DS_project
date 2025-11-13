"""Cookie helpers shared by the interactive shopping CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

SPECIAL_SECURE_COOKIES = {"_abck", "bm_sz", "bm_sv", "ak_bmsc", "bm_so"}


def load_cookie_text(cookie_file: Optional[str]) -> Optional[str]:
    """Read cookie text from disk if a path is provided."""
    if not cookie_file:
        return None

    path = Path(cookie_file).expanduser()
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip()


def build_cookie_header(raw_cookie: Optional[str]) -> Optional[str]:
    """Convert JSON cookie blobs into a standard Cookie header string."""
    if not raw_cookie:
        return None

    try:
        data = json.loads(raw_cookie)
    except json.JSONDecodeError:
        return raw_cookie.strip() or None

    if isinstance(data, dict):
        items = [data]
    elif isinstance(data, list):
        items = [item for item in data if isinstance(item, dict)]
    else:
        items = []

    parts = []
    for item in items:
        name = item.get("name")
        value = item.get("value")
        if not name or value is None:
            continue
        parts.append(f"{name}={value}")
    return "; ".join(parts) if parts else None


def parse_cookie_records(raw_cookie: Optional[str]) -> List[Dict[str, Any]]:
    """Return Playwright-compatible cookie dictionaries from raw text."""
    if not raw_cookie:
        return []

    try:
        data = json.loads(raw_cookie)
    except json.JSONDecodeError:
        data = None

    cookies: List[Dict[str, Any]] = []

    if isinstance(data, dict):
        cookies = [data]
    elif isinstance(data, list):
        cookies = [item for item in data if isinstance(item, dict)]

    if cookies:
        return cookies

    for line in raw_cookie.split(";"):
        line = line.strip()
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        cookie: Dict[str, Any] = {
            "name": name.strip(),
            "value": value.strip(),
            "domain": ".coupang.com",
            "path": "/",
        }
        if cookie["name"] in SPECIAL_SECURE_COOKIES:
            cookie.update({"secure": True, "httpOnly": True, "sameSite": "None"})
        cookies.append(cookie)

    return cookies
