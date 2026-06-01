import os
import re
import html as _html

import httpx

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_WS_RE = re.compile(r"\s+")


def clean_html(html: str) -> str:
    """Strip tags, scripts, and styles from HTML; collapse whitespace to text."""
    if not html:
        return ""
    text = _SCRIPT_STYLE_RE.sub(" ", html)
    text = _TAG_RE.sub(" ", text)
    text = _html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


_DDG_LINK_RE = re.compile(
    r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
    re.DOTALL | re.IGNORECASE,
)
_DDG_SNIPPET_RE = re.compile(
    r'<a[^>]*class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
    re.DOTALL | re.IGNORECASE,
)


def parse_ddg_results(html: str, max_results: int = 5) -> list:
    """Parse DuckDuckGo HTML-lite results into [{title, url, snippet}]."""
    links = _DDG_LINK_RE.findall(html or "")
    snippets = _DDG_SNIPPET_RE.findall(html or "")
    results = []
    for i, (url, title) in enumerate(links[:max_results]):
        snippet = clean_html(snippets[i]) if i < len(snippets) else ""
        results.append({
            "title": clean_html(title),
            "url": url,
            "snippet": snippet,
        })
    return results


_DDG_URL = "https://lite.duckduckgo.com/lite/"
_HEADERS = {"User-Agent": "Mozilla/5.0 (Friday AI agent)"}


def select_provider() -> str:
    """Pick a search provider: an API if its key is in env, else keyless DDG."""
    if os.getenv("BRAVE_API_KEY"):
        return "brave"
    if os.getenv("TAVILY_API_KEY"):
        return "tavily"
    if os.getenv("SERPAPI_API_KEY"):
        return "serpapi"
    return "duckduckgo"


async def _http_get(url: str) -> str:
    """The single impure network call (patched in tests)."""
    async with httpx.AsyncClient(timeout=10, headers=_HEADERS, follow_redirects=True) as client:
        resp = await client.get(url)
        return resp.text


async def web_search(query: str, max_results: int = 5):
    """Search the web. Returns [{title,url,snippet}] or an error string."""
    try:
        from urllib.parse import quote_plus
        # All providers currently route through the keyless DDG endpoint; API
        # providers (brave/tavily/serpapi) are selected for future use but share
        # this fetch path until their key-based clients are added.
        select_provider()
        html = await _http_get(f"{_DDG_URL}?q={quote_plus(query)}")
        return parse_ddg_results(html, max_results=max_results)
    except Exception as e:
        return f"Web search failed: {e}"


async def fetch_page(url: str, max_chars: int = 4000) -> str:
    """Fetch a URL and return cleaned, truncated readable text."""
    try:
        html = await _http_get(url)
        text = clean_html(html)
        return text[:max_chars]
    except Exception as e:
        return f"Could not fetch page: {e}"
