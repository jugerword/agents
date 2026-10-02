import os

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

_openai_api_key = os.getenv("OPENAI_API_KEY")
_tavily_api_key = os.getenv("TAVILY_API_KEY")
_tavily_client = None


def get_tavily_client() -> TavilyClient:
    """Lazily instantiate the TavilyClient to avoid failing at import time
    when the API is unreachable or no key is configured yet."""
    global _tavily_client
    if _tavily_client is None:
        if not _tavily_api_key:
            raise ValueError(
                "TAVILY_API_KEY is not set. Set it in your .env file before "
                "using the Tavily search connector."
            )
        _tavily_client = TavilyClient(api_key=_tavily_api_key)
    return _tavily_client


def get_search_context(query: str) -> str:
    """Run a Tavily context search and return the context string for RAG use."""
    client = get_tavily_client()
    return client.get_search_context(query=query)
