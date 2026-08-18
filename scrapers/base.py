"""
Shared fetch + clean helpers for government portal scrapers.
Be polite: delay between requests, clear User-Agent.
"""

from __future__ import annotations

import time
import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "NyayaSahayakBot/1.0 (SIH2026 research; educational use)"
}

DEFAULT_DELAY_SEC = 2.0


def fetch(url: str, delay: float = DEFAULT_DELAY_SEC) -> str:
    """
    Fetch a page with a polite delay.
    Raises httpx.HTTPStatusError if the site blocks/refuses.
    """
    time.sleep(delay)
    headers = {
        **HEADERS,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
        "Cache-Control": "no-cache",
    }
    with httpx.Client(headers=headers, timeout=30.0, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def safe_fetch(url: str, delay: float = DEFAULT_DELAY_SEC) -> str | None:
    """Fetch page text, or return None if blocked/failed."""
    try:
        return fetch(url, delay=delay)
    except Exception as e:
        print(f"Warning: could not fetch {url} ({e.__class__.__name__}: {e})")
        return None
        
def clean_html(html: str) -> str:
    """Strip scripts/nav/footer and return visible text."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    # collapse excessive blank lines
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines)