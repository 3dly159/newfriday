from core.agency.web import clean_html, parse_ddg_results


def test_clean_html_strips_tags_and_scripts():
    html = "<html><head><style>x{}</style></head><body><script>bad()</script><p>Hello <b>Sir</b></p></body></html>"
    out = clean_html(html)
    assert "Hello" in out and "Sir" in out
    assert "<" not in out and "bad()" not in out and "x{}" not in out


def test_clean_html_collapses_whitespace():
    assert clean_html("<p>a</p>\n\n\n   <p>b</p>") == "a b"


def test_parse_ddg_results_extracts_links():
    html = '''
    <div><a class="result__a" href="https://example.com/a">First Result</a>
    <a class="result__snippet">Snippet one.</a></div>
    <div><a class="result__a" href="https://example.com/b">Second Result</a>
    <a class="result__snippet">Snippet two.</a></div>
    '''
    results = parse_ddg_results(html, max_results=5)
    assert len(results) == 2
    assert results[0]["title"] == "First Result"
    assert results[0]["url"] == "https://example.com/a"
    assert "Snippet one." in results[0]["snippet"]


def test_parse_ddg_results_respects_max():
    html = ''.join(f'<a class="result__a" href="http://e/{i}">R{i}</a>' for i in range(10))
    assert len(parse_ddg_results(html, max_results=3)) == 3


import asyncio
from core.agency import web as webmod
from core.agency.web import select_provider, web_search, fetch_page


def test_select_provider_keyless_by_default(monkeypatch):
    for k in ("BRAVE_API_KEY", "TAVILY_API_KEY", "SERPAPI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    assert select_provider() == "duckduckgo"


def test_select_provider_prefers_api_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    monkeypatch.setenv("BRAVE_API_KEY", "x")
    assert select_provider() == "brave"


def test_web_search_uses_ddg_fetch(monkeypatch):
    sample = '<a class="result__a" href="http://e/1">Title</a><a class="result__snippet">Snip</a>'
    async def fake_get(url):
        return sample
    monkeypatch.setattr(webmod, "_http_get", fake_get)
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    results = asyncio.run(web_search("anything"))
    assert results[0]["title"] == "Title"


def test_fetch_page_cleans_and_truncates(monkeypatch):
    async def fake_get(url):
        return "<p>" + ("word " * 1000) + "</p>"
    monkeypatch.setattr(webmod, "_http_get", fake_get)
    out = asyncio.run(fetch_page("http://x", max_chars=50))
    assert len(out) <= 50
    assert "<" not in out


def test_web_search_network_error_returns_message(monkeypatch):
    async def boom(url):
        raise ConnectionError("down")
    monkeypatch.setattr(webmod, "_http_get", boom)
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    out = asyncio.run(web_search("q"))
    assert isinstance(out, str) and "search" in out.lower()
