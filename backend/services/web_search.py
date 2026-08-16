# Tavily-backed external source search

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from langchain_core.documents import Document

from backend.config import get_settings


def search_web(question: str) -> list[Document]:
    settings = get_settings()
    if not settings.tavily_api_key:
        return []

    payload = json.dumps(
        {
            "api_key": settings.tavily_api_key,
            "query": question,
            "search_depth": "advanced",
            "max_results": settings.web_search_results,
            "include_answer": False,
            "include_raw_content": False,
        }
    ).encode("utf-8")
    request = Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            data = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError("External web search is temporarily unavailable") from error

    return [
        Document(
            page_content=str(result.get("content", "")),
            metadata={
                "source_type": "web",
                "title": str(result.get("title", "Web result")),
                "url": str(result.get("url", "")),
                "score": result.get("score"),
            },
        )
        for result in data.get("results", [])
        if result.get("content") and result.get("url")
    ]
