from __future__ import annotations

from typing import Any

import requests

from .models import Article, RankedSummary, Region
from .utils import extract_json_block


class GeminiSummarizer:
    def __init__(
        self, api_key: str, model: str = "gemini-2.5-flash", timeout_seconds: int = 20
    ):
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def _build_prompt(self, articles: list[Article], region: Region, top_n: int) -> str:
        lines: list[str] = []
        for idx, article in enumerate(articles, start=1):
            lines.append(
                f"[{idx}] title={article.title} | description={article.description[:320]}"
            )

        # region_label = "日本" if region == "japan" else "海外"
        # return (
        #     "あなたはITニュース専門の編集者です。候補記事から重要度順に上位を選び、各記事を要約してください。\n"
        #     f"対象: {region_label}\n"
        #     f"上位件数: {top_n}\n"
        #     "ルール:\n"
        #     "- 出力はビジネスパーソン向けの自然で読みやすい日本語\n"
        #     "- 技術専門用語は正確に維持する\n"
        #     "- 英語記事は文脈を踏まえて日本語に意訳する\n"
        #     "- URLは絶対に含めない\n"
        #     "- 1記事につき要約は箇条書き1点のみ\n"
        #     "- タイトルは日本語訳を含める\n"
        #     "- 出力形式は以下を厳守する\n"
        #     "  1. [日本語タイトル]\n"
        #     "     - [読みやすい日本語で要約した内容]\n"
        #     "- 候補外の事実を創作しない\n"
        #     "出力は JSON のみ。\n"
        #     '{"items":[{"index":1,"title_ja":"...","summary":"..."}]}'
        #     "\n候補一覧:\n"
        #     + "\n".join(lines)
        # )

        region_label = "ဂျပန် (Japan)" if region == "japan" else "နိုင်ငံတကာ (Global)"

        return (
            "あなたはITニュース専門の編集者です。候補記事から重要度順に上位を選び、各記事を要約してください。\n"
            f"対象ソース: {region_label}\n"
            f"上位件数: {top_n}\n"
            "ルール:\n"
            "- 出力は【全て】ビジネスパーソン向けの自然で読みやすいミャンマー語（ビルマ語）で行うこと（ソースが日本語や英語であっても、出力は必ずミャンマー語にすること）\n"
            "- 技術専門用語は正確に維持する\n"
            "- ソース記事（日本語・英語）の内容は、文脈を踏まえて自然なミャンマー語に意訳する\n"
            "- URLは絶対に含めない\n"
            "- 1記事につき要約は箇条書き1点のみ（ミャンマー語で記述する）\n"
            "- タイトルも必ずミャンマー語に翻訳すること\n"
            "- 出力形式は以下を厳守する\n"
            "  1. [ミャンマー語タイトル]\n"
            "     - [読みやすいミャンマー語で要約した内容]\n"
            "- 候補外の事実を創作しない\n"
            "出力は JSON のみ。\n"
            '{"items":[{"index":1,"title_my":"...","summary":"..."}]}'
            "\n候補一覧:\n" + "\n".join(lines)
        )

    def rank_and_summarize(
        self, articles: list[Article], region: Region, top_n: int
    ) -> list[RankedSummary]:
        if not articles:
            return []

        limited = articles[: min(len(articles), 50)]
        prompt = self._build_prompt(limited, region=region, top_n=top_n)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
            },
        }

        try:
            resp = requests.post(
                url,
                params={"key": self.api_key},
                json=payload,
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = extract_json_block(text)
            return self._to_ranked_summaries(
                parsed, limited, region=region, top_n=top_n
            )
        except Exception:
            return self._fallback_rank(limited, region=region, top_n=top_n)

    def _to_ranked_summaries(
        self,
        payload: dict[str, Any],
        articles: list[Article],
        region: Region,
        top_n: int,
    ) -> list[RankedSummary]:
        out: list[RankedSummary] = []
        used_titles: set[str] = set()

        for row in payload.get("items", [])[:top_n]:
            try:
                index = int(row["index"]) - 1
                article = articles[index]
            except Exception:
                continue

            title_ja = (row.get("title_ja") or "").strip() or article.title
            summary_text = (row.get("summary") or "").strip()
            if not summary_text:
                continue
            summary = f"- {summary_text}"

            out.append(
                RankedSummary(
                    title=title_ja,
                    url=article.url,
                    source=article.source,
                    published_at=article.published_at,
                    summary=summary,
                    region=region,
                )
            )
            used_titles.add(article.title)

        if not out:
            return self._fallback_rank(articles, region=region, top_n=top_n)
        if len(out) < top_n:
            for item in self._fallback_rank(articles, region=region, top_n=top_n):
                if item.title in used_titles:
                    continue
                out.append(item)
                if len(out) >= top_n:
                    break
        return out

    def _fallback_rank(
        self, articles: list[Article], region: Region, top_n: int
    ) -> list[RankedSummary]:
        out: list[RankedSummary] = []
        sorted_articles = sorted(articles, key=lambda x: x.published_at, reverse=True)[
            :top_n
        ]
        for article in sorted_articles:
            snippet = article.description.replace("\n", " ").strip()
            snippet = snippet[:120] + ("..." if len(snippet) > 120 else "")
            summary = snippet or "主要な技術動向を把握できるニュースです。"
            out.append(
                RankedSummary(
                    title=article.title,
                    url=article.url,
                    source=article.source,
                    published_at=article.published_at,
                    summary=f"- {summary}",
                    region=region,
                )
            )
        return out
