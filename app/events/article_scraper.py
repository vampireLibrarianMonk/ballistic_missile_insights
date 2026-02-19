"""Article scraping utilities for ORRG news summarization."""

from __future__ import annotations

from typing import Optional

from newspaper import Article


def fetch_article_text(url: str, timeout: int = 12) -> Optional[str]:
    """Fetch full article text using newspaper3k."""
    if not url:
        return None

    article = Article(url)
    article.download()
    try:
        article.parse()
    except Exception:
        return None
    if not article.text:
        return None
    return article.text.strip()