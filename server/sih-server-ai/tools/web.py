from ddgs import DDGS


MAX_SEARCH_RESULTS = 5
MAX_FETCH_CHARS = 12000


def web_search(query):
    """
    Search the web and return compact results.

    The LLM receives titles, URLs, and snippets only.
    """

    if not isinstance(query, str) or not query.strip():
        return {
            "success": False,
            "error": "Search query must be a non-empty string.",
        }

    query = query.strip()

    try:
        results = DDGS(
            timeout=8,
        ).text(
            query,
            region="us-en",
            safesearch="moderate",
            max_results=MAX_SEARCH_RESULTS,
        )

        formatted = []

        for result in results:

            formatted.append({
                "title": result.get("title", ""),
                "url": result.get("href", ""),
                "snippet": result.get("body", ""),
            })

        return {
            "success": True,
            "query": query,
            "results": formatted,
        }

    except Exception as error:

        return {
            "success": False,
            "query": query,
            "error": f"Web search failed: {error}",
        }


def fetch_url(url):
    """
    Fetch and extract readable text from a webpage.
    """

    if not isinstance(url, str) or not url.strip():
        return {
            "success": False,
            "error": "URL must be a non-empty string.",
        }

    url = url.strip()

    try:
        result = DDGS(
            timeout=10,
        ).extract(
            url,
            fmt="text_markdown",
        )

        content = result.get(
            "content",
            "",
        )

        if len(content) > MAX_FETCH_CHARS:
            content = (
                content[:MAX_FETCH_CHARS]
                + "\n\n[Content truncated]"
            )

        return {
            "success": True,
            "url": result.get("url", url),
            "content": content,
        }

    except Exception as error:

        return {
            "success": False,
            "url": url,
            "error": f"URL fetch failed: {error}",
        }


def register_tools(registry):
    """Register web tools."""

    registry.register(
        name="web_search",
        description=(
            "Search the public web for information and return "
            "relevant pages with titles, URLs, and snippets. "
            "Use this only when the current browser page cannot "
            "provide the requested information or destination."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for.",
                }
            },
            "required": ["query"],
        },
        handler=web_search,
        category="web",
        state_effect="none",
        risk="safe",
    )

    registry.register(
        name="fetch_url",
        description=(
            "Fetch and read the text content of a specific "
            "webpage URL."
        ),
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": (
                        "The webpage URL to retrieve."
                    ),
                }
            },
            "required": ["url"],
        },
        handler=fetch_url,
        category="web",
        state_effect="none",
        risk="safe",
    )
