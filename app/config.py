from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    news_api_key: str
    gemini_api_key: str
    line_channel_access_token: str
    line_user_id: str
    gemini_model: str
    top_n: int
    request_timeout_seconds: int



def load_settings() -> Settings:
    load_dotenv()

    return Settings(
        news_api_key=os.getenv("NEWS_API_KEY", "").strip(),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        line_channel_access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip(),
        line_user_id=os.getenv("LINE_USER_ID", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip(),
        top_n=int(os.getenv("TOP_N", "5")),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20")),
    )
