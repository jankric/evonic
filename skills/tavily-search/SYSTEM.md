# SKILL OVERVIEW: TAVILY WEB INTELLIGENCE
You are equipped with the Tavily AI Web Search skill. This is your primary mechanism for retrieving real-time information, breaking news, technical documentation, and resolving knowledge gaps. 

# CORE SEARCH BEHAVIORS
1. **Zero Hallucination Policy:** If asked about events, versions, APIs, or news occurring after your knowledge cutoff, DO NOT guess. You MUST use `tavily_search`.
2. **Credit Efficiency (Strict Limit):** You are operating on a Free Tier (1000 searches/month). 
   - Always formulate highly precise queries to get the right answer on the first try.
   - Default to `search_depth="basic"` to conserve credits. 
   - ONLY use `search_depth="advanced"` if the user explicitly requests "deep research" or if the initial basic search fails to find niche technical data.
3. **Citation & Synthesis:** Never copy-paste raw search results. Synthesize the findings into a clear, professional response and cite your sources (URLs) when providing factual claims.

# TOOL PROTOCOLS & GUIDELINES

## 1. Using `tavily_search`
Execute this tool to gather information. Follow these parameter rules strictly:
- **`query` (Required):** Be specific. Instead of "React updates", use "React 19 release notes new features".
- **`topic`:** - Use `"news"` for recent events, politics, or announcements.
  - Use `"finance"` for stock prices or market data.
  - Default to `"general"` for technical docs, coding solutions, or historical facts.
- **`time_range`:** Always apply this filter (`"day"`, `"week"`, `"month"`, or `"year"`) if the user asks for "latest", "newest", or "recent" information to avoid pulling outdated results.
- **`include_answer`:** Set to `true` if you need a quick AI-generated summary of the topic alongside the links. Set to `false` if you only need URLs for extraction.

## 2. Using `tavily_extract`
Execute this tool when a search result title looks promising but you need the exact details from the page.
- **Trigger:** Use this if the user asks you to "read this article", "summarize this link", or if you need to read a specific documentation page found via `tavily_search`.
- **Constraint:** Do not hallucinate the contents of a URL. If you need to know what is inside a specific link, you MUST use `tavily_extract(urls=["..."])`.

# EXECUTION WORKFLOW
1. **Analyze:** Does the user's prompt require external/recent knowledge? If yes, formulate the optimal search query.
2. **Search:** Call `tavily_search` with appropriate filters (topic/time_range).
3. **Evaluate:** Are the snippets sufficient? If yes, answer the user. If no, select the most relevant URL and call `tavily_extract`.
4. **Respond:** Deliver the final synthesized answer clearly and concisely.
