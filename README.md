# Substack MCP server

A read-only [Model Context Protocol](https://modelcontextprotocol.io) server that lets Claude or any MCP client search Substack, list a publication's posts and read them. It uses Substack's public JSON endpoints, so it needs no login, no cookies and no API key.

I wrote it because the official Substack connector is limited to a publication's admin and its own analytics. This one works on any public publication.

## Tools

| Tool | What it does |
| --- | --- |
| `search_substack(query, limit)` | Search all of Substack for posts and profiles |
| `list_posts(publication, search, limit, sort)` | List a publication's posts, newest first or top by likes, with optional search inside it |
| `read_post(url)` | Return the full text of one post from its URL |
| `read_feed(publication, limit)` | Return the latest posts of a publication in full, for a quick digest |

`publication` can be a subdomain (`ruben`), a full `x.substack.com` host or a custom domain.

## Run it

The script declares its own dependencies, so [uv](https://docs.astral.sh/uv/) is the only thing you need:

```
uv run --script server.py
```

Register it with Claude Code:

```
claude mcp add substack -s user -- uv run --quiet --script /absolute/path/to/server.py
```

## Notes

- Paid-only posts return the free preview only. The server does not try to get past the paywall.
- The endpoints are not an official, documented API, so they can change without notice.
- `mcp` is pinned below 2.0 because version 2 renamed `FastMCP`.
- Nested HTML elements can repeat a paragraph, so the text extractor removes duplicate lines.
