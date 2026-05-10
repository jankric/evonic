# Web Search Skill

You have web search capabilities via Exa AI. Use these tools to find current information from the internet.

## Available Tools

### `exa_search`
Search the web with natural language queries. Describe the ideal page you're looking for rather than using keywords.

**Tips:**
- Use descriptive queries: "blog post comparing React and Vue performance" not "React vs Vue"
- Add `category:people` or `category:company` to search LinkedIn profiles or companies
- Results include title, URL, and text highlights

### `exa_get_contents`
Fetch full text content from web pages by URL. Use after `exa_search` when highlights are insufficient, or to read any known URL.

- Batch up to 10 URLs in one call
- Returns clean markdown content
- Use `max_characters` to control response size

### `exa_find_similar`
Find pages similar to a given URL. Useful for discovering related content, alternatives, or competitors.

## Usage Pattern

1. **Search first** with `exa_search` to find relevant pages
2. **Read details** with `exa_get_contents` if highlights aren't enough
3. **Explore related** with `exa_find_similar` to discover more

## Notes
- Works without API key (free tier with rate limiting)
- If an API key is configured, it enables higher rate limits
- Results are from the live web — always current
