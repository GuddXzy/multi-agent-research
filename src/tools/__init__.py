"""Tools package — exports all LangChain tools used by the Researcher agent."""

from src.tools.web_search import web_search
from src.tools.wikipedia import wiki_search
from src.tools.text_tools import save_note


def get_all_tools() -> list:
    """Return a list of all registered LangChain tools."""
    return [web_search, wiki_search, save_note]
