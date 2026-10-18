# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=1.2,<2", "httpx", "beautifulsoup4"]
# ///
"""Read-only Substack MCP server. Uses Substack's public JSON endpoints; no login, no cookies.
Paid-only posts return the free preview only."""
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("substack")
HTTP = httpx.Client(headers={"User-Agent": "Mozilla/5.0"}, timeout=20, follow_redirects=True)


def _base(publication: str) -> str:
    """Accept 'ruben', 'ruben.substack.com', a custom domain, or any URL on the publication."""
    p = publication.strip()
    if "://" in p:
        p = urlparse(p).netloc
    if "." not in p:
        p += ".substack.com"
    return "https://" + p


def _text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style", "figure", "button"]):
        tag.decompose()
    lines = []
    for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "pre", "blockquote"]):
        if el.find_parent(["li", "blockquote"]) and el.name in ("p", "li"):
            continue
        t = el.get_text(" ", strip=True)
        if not t:
            continue
        if el.name in ("h1", "h2", "h3", "h4"):
            t = "#" * int(el.name[1]) + " " + t
        elif el.name == "li":
            t = "- " + t
        lines.append(t)
        for a in el.find_all("a", href=True):
            if a["href"].startswith("http") and "substack.com/subscribe" not in a["href"]:
                lines.append(f"  [link: {a.get_text(strip=True)[:60]}]({a['href']})")
    return "\n\n".join(dict.fromkeys(lines))


def _row(p: dict, base: str = "") -> str:
    url = p.get("canonical_url") or f"{base}/p/{p.get('slug')}"
    paid = " [paid]" if p.get("audience") == "only_paid" else ""
    return f"- {p.get('post_date', '')[:10]} | {p.get('title')}{paid} | {p.get('reaction_count', 0)} likes | {url}\n  {p.get('subtitle') or ''}".rstrip()


@mcp.tool()
def search_substack(query: str, limit: int = 10) -> str:
    """Search all of Substack for posts and publications matching a query (e.g. 'claude code mcp')."""
    d = HTTP.get("https://substack.com/api/v1/top/search", params={"query": query}).json()
    pubs, posts = [], []
    for it in d.get("items", []):
        if it["type"] == "profileSearchResults":
            pubs += [f"- {r.get('name')} (@{r.get('handle')})" for r in it.get("results", [])[:5]]
        elif it["type"] == "post" and it.get("post"):
            posts.append(_row(it["post"]) + f"\n  in: {it.get('publication', {}).get('name')}")
    return "Posts:\n" + "\n".join(posts[:limit]) + ("\n\nProfiles:\n" + "\n".join(pubs) if pubs else "")


@mcp.tool()
def list_posts(publication: str, search: str = "", limit: int = 15, sort: str = "new") -> str:
    """List a publication's posts, newest first (sort='top' for most liked). Optional search within it.
    publication: subdomain like 'ruben', 'x.substack.com', or a custom domain."""
    base = _base(publication)
    params = {"sort": sort, "limit": min(limit, 50)}
    if search:
        params["search"] = search
    posts = HTTP.get(f"{base}/api/v1/archive", params=params).json()
    return f"{base}\n" + "\n".join(_row(p, base) for p in posts)


@mcp.tool()
def read_post(url: str) -> str:
    """Read the full text of a Substack post from its URL (https://<pub>/p/<slug>). Paid posts return the preview."""
    u = urlparse(url)
    m = re.search(r"/p/([^/?#]+)", u.path)
    if not m:
        return "Not a post URL: expected https://<publication>/p/<slug>"
    p = HTTP.get(f"https://{u.netloc}/api/v1/posts/{m.group(1)}").json()
    note = "\n(Paid post: only the free preview is available.)" if p.get("audience") == "only_paid" else ""
    return f"# {p.get('title')}\n{p.get('subtitle') or ''}\n{p.get('post_date', '')[:10]} | {p.get('reaction_count', 0)} likes{note}\n\n{_text(p.get('body_html') or p.get('truncated_body_text') or '')}"


@mcp.tool()
def read_feed(publication: str, limit: int = 5) -> str:
    """Read the latest posts of a publication in full (free posts), for a quick digest."""
    base = _base(publication)
    posts = HTTP.get(f"{base}/api/v1/archive", params={"sort": "new", "limit": limit}).json()
    return "\n\n---\n\n".join(read_post(p.get("canonical_url") or f"{base}/p/{p['slug']}")[:6000] for p in posts)


if __name__ == "__main__":
    mcp.run()
