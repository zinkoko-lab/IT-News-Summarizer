from __future__ import annotations

from dataclasses import asdict

from .config import Settings
from .formatter import build_summary_text_message, build_text_message
from .line_client import LineClient
from .models import RankedSummary
from .sources import SourceClient
from .summarizer import GeminiSummarizer
from .utils import deduplicate_articles


def run_pipeline(settings: Settings, include_qiita_zenn: bool = True) -> dict:
    if not settings.news_api_key:
        raise ValueError("NEWS_API_KEY is required")
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is required")
    if not settings.line_channel_access_token:
        raise ValueError("LINE_CHANNEL_ACCESS_TOKEN is required")
    if not settings.line_user_id:
        raise ValueError("LINE_USER_ID is required")

    source_client = SourceClient(
        news_api_key=settings.news_api_key,
        timeout_seconds=settings.request_timeout_seconds,
    )
    summarizer = GeminiSummarizer(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        timeout_seconds=settings.request_timeout_seconds,
    )
    line_client = LineClient(
        channel_access_token=settings.line_channel_access_token,
        timeout_seconds=settings.request_timeout_seconds,
    )

    fetch_limit = 50
    top_n = min(max(settings.top_n, 1), 5)
    global_raw, japan_raw = source_client.fetch_all(limit_per_category=fetch_limit)
    global_unique = deduplicate_articles(global_raw)[:fetch_limit]
    japan_unique = deduplicate_articles(japan_raw)[:fetch_limit]

    global_ranked = summarizer.rank_and_summarize(global_unique, region="global", top_n=top_n)[:top_n]
    japan_ranked = summarizer.rank_and_summarize(japan_unique, region="japan", top_n=top_n)[:top_n]

    messages: list[dict] = [build_text_message(global_count=len(global_ranked), japan_count=len(japan_ranked))]
    messages.append(build_summary_text_message(global_ranked, region="global"))
    messages.append(build_summary_text_message(japan_ranked, region="japan"))
    line_client.push_messages(to=settings.line_user_id, messages=messages)

    return {
        "global_candidates": len(global_unique),
        "japan_candidates": len(japan_unique),
        "global_sent": len(global_ranked),
        "japan_sent": len(japan_ranked),
        "global_items": [_to_log_dict(x) for x in global_ranked],
        "japan_items": [_to_log_dict(x) for x in japan_ranked],
    }


def _to_log_dict(item: RankedSummary) -> dict:
    data = asdict(item)
    data["published_at"] = item.published_at.isoformat()
    return data
