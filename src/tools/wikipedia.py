"""Wikipedia search tool."""

from langchain_core.tools import tool


@tool
def wiki_search(query: str) -> str:
    """Search Wikipedia for factual background information about a topic.

    Use this for definitions, history, established facts, and overviews.
    Returns the page summary (up to 2000 characters).
    """
    try:
        import wikipedia

        wikipedia.set_lang("en")

        # Find candidate pages
        candidates = wikipedia.search(query, results=3)
        if not candidates:
            return f"No Wikipedia articles found for: {query}"

        # Try candidates in order until one works
        for title in candidates:
            try:
                page = wikipedia.page(title, auto_suggest=False)
                summary = page.summary[:2000]
                return f"**{page.title}**\n\n{summary}"

            except wikipedia.exceptions.DisambiguationError as e:
                # Take first unambiguous option
                if e.options:
                    try:
                        page = wikipedia.page(e.options[0], auto_suggest=False)
                        summary = page.summary[:2000]
                        return f"**{page.title}**\n\n{summary}"
                    except Exception:
                        continue

            except wikipedia.exceptions.PageError:
                continue

        return f"No Wikipedia page found for: {query}"

    except Exception as exc:
        return f"Wikipedia search failed for '{query}': {exc}"
