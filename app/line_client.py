from __future__ import annotations

import requests


class LineClient:
    def __init__(self, channel_access_token: str, timeout_seconds: int = 20):
        self.channel_access_token = channel_access_token
        self.timeout_seconds = timeout_seconds

    def push_messages(self, to: str, messages: list[dict]) -> None:
        if not messages:
            return

        url = "https://api.line.me/v2/bot/message/push"
        headers = {
            "Authorization": f"Bearer {self.channel_access_token}",
            "Content-Type": "application/json",
        }

        # LINE Messaging APIは1リクエスト最大5メッセージ
        for i in range(0, len(messages), 5):
            batch = messages[i : i + 5]
            payload = {"to": to, "messages": batch}
            resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout_seconds)
            resp.raise_for_status()
