# Web Search (Exa) Skill

## Overview
You now have web search capabilities powered by Exa AI. You can search the internet, read web page contents, and find similar pages.

## Available Tools

### `exa_search`
Search the web with a query. Supports neural (semantic) and keyword search.

**Best practices:**
- Use **natural language** queries for neural mode: "latest advances in quantum computing 2025"
- Use **keyword** queries for specific lookups: "python requests library timeout"
- Use `type: "auto"` (default) to let Exa pick the best mode
- Set `include_text: true` if you need page content inline (slower but saves a follow-up call)
- Use `include_domains` to restrict to trusted sources
- Use `start_published_date` for recent content

### `exa_get_contents`
Fetch and read the text content of web pages by URL. Use this after `exa_search` to read specific results in detail.

**Best practices:**
- Pass up to 10 URLs at once for efficiency
- Use `max_characters` to control response size (default 3000)
- Good for reading articles, docs, blog posts

### `exa_find_similar`
Find pages similar to a given URL. Great for discovering alternatives, related resources, or competitor analysis.

## Usage Patterns

**Research a topic:**
1. `exa_search` with a descriptive query
2. `exa_get_contents` on the most relevant URLs

**Find alternatives:**
1. `exa_find_similar` with a known URL

**Get recent news:**
1. `exa_search` with `category: "news"` and `start_published_date`

## Notes
- Results include title, URL, published date, and optionally text content
- The API key is configured in the skill settings — if you get auth errors, ask the admin to set the Exa API key
