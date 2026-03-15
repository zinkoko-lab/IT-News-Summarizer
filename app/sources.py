from __future__ import annotations

import time
from datetime import timedelta
from typing import Any

import requests

from .models import Article
from .utils import now_utc, parse_datetime, within_last_24_hours


class SourceClient:
    def __init__(self, news_api_key: str, timeout_seconds: int = 20):
        self.news_api_key = news_api_key
        self.timeout_seconds = timeout_seconds

    def _get_json_with_retry(self, url: str, params: dict[str, Any] | None = None, retries: int = 3) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                resp = requests.get(url, params=params, timeout=self.timeout_seconds)
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:
                last_error = exc
                if attempt < retries:
                    time.sleep(1.2 * attempt)
        raise RuntimeError(f"failed after retries: {url}") from last_error

    def _newsapi_to_articles(
        self,
        payload: dict[str, Any],
        region: str,
        fallback_source: str,
        require_recent: bool = True,
    ) -> list[Article]:
        out: list[Article] = []
        for item in payload.get("articles", []):
            title = (item.get("title") or "").strip()
            url = (item.get("url") or "").strip()
            description = (item.get("description") or "").strip() or title
            published_at = parse_datetime(item.get("publishedAt"))

            if not title or not description or not url:
                continue
            if require_recent and not within_last_24_hours(published_at):
                continue
            if published_at is None:
                # 取得は許可しつつ、時刻欠損は現在時刻で補完
                published_at = now_utc()

            source = (item.get("source") or {}).get("name") or fallback_source
            out.append(
                Article(
                    title=title,
                    url=url,
                    description=description,
                    source=source,
                    published_at=published_at,
                    region=region,
                )
            )
        return out

    def fetch_global_it_news(self, limit: int = 50) -> list[Article]:
        """Global: AI, Technology, Global Trend で検索。"""
        target = min(max(limit, 1), 50)
        url = "https://newsapi.org/v2/everything"
        from_utc = (now_utc() - timedelta(hours=24)).isoformat(timespec="seconds")
        primary_params = {
            "apiKey": self.news_api_key,
            "q": 'AI OR Technology OR "Global Trend"',
            "language": "en",
            "sortBy": "publishedAt",
            "from": from_utc,
            "pageSize": target,
        }
        fallback_params = {
            "apiKey": self.news_api_key,
            "q": 'AI OR Technology OR "Global Trend"',
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": target,
        }

        articles: list[Article] = []
        payload = self._get_json_with_retry(url, params=primary_params)
        articles.extend(
            self._newsapi_to_articles(payload, region="global", fallback_source="NewsAPI Global", require_recent=True)
        )
        if len(articles) < target:
            payload2 = self._get_json_with_retry(url, params=fallback_params)
            articles.extend(
                self._newsapi_to_articles(
                    payload2,
                    region="global",
                    fallback_source="NewsAPI Global",
                    require_recent=False,
                )
            )
        return articles[:target]

    def fetch_japan_it_news(self, limit: int = 50) -> list[Article]:
        """Japan: country=jp, category=technology。"""
        target = min(max(limit, 1), 50)

        top_headlines_url = "https://newsapi.org/v2/top-headlines"
        top_headlines_params = {
            "apiKey": self.news_api_key,
            "country": "jp",
            "category": "technology",
            "pageSize": target,
        }

        everything_url = "https://newsapi.org/v2/everything"
        from_utc = (now_utc() - timedelta(hours=72)).isoformat(timespec="seconds")
        fallback_params = {
            "apiKey": self.news_api_key,
            "q": "AI OR テクノロジー OR IT OR クラウド",
            "language": "jp",
            "sortBy": "publishedAt",
            "from": from_utc,
            "pageSize": target,
        }

        articles: list[Article] = []
        payload = self._get_json_with_retry(top_headlines_url, params=top_headlines_params)
        articles.extend(
            self._newsapi_to_articles(payload, region="japan", fallback_source="NewsAPI JP", require_recent=True)
        )
        if len(articles) < target:
            payload2 = self._get_json_with_retry(everything_url, params=fallback_params)
            articles.extend(
                self._newsapi_to_articles(
                    payload2,
                    region="japan",
                    fallback_source="NewsAPI JP",
                    require_recent=False,
                )
            )
        return articles[:target]

    def fetch_all(self, limit_per_category: int = 50) -> tuple[list[Article], list[Article]]:
        global_articles: list[Article] = []
        japan_articles: list[Article] = []

        try:
            global_articles = self.fetch_global_it_news(limit=limit_per_category)
        except Exception:
            global_articles = []

        try:
            japan_articles = self.fetch_japan_it_news(limit=limit_per_category)
        except Exception:
            japan_articles = []

        return global_articles[:limit_per_category], japan_articles[:limit_per_category]
