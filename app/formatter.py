from __future__ import annotations

from .models import RankedSummary, Region


def build_summary_text_message(items: list[RankedSummary], region: Region) -> dict:
    title = "Global Top 5" if region == "global" else "Japan Top 5"
    lines: list[str] = [title]

    for idx, item in enumerate(items[:5], start=1):
        lines.append(f"{idx}. [{item.title}]")
        lines.append(item.summary)
        lines.append(f"URL: {item.url}")
        lines.append("")

    text = "\n".join(lines).strip()
    if len(text) > 4900:
        text = text[:4900] + "..."

    return {
        "type": "text",
        "text": text,
    }


def build_text_message(global_count: int, japan_count: int) -> dict:
    return {
        "type": "text",
        "text": (
            "IT News Summarizer 完了\n"
            f"Global: {global_count}件\n"
            f"Japan: {japan_count}件"
        ),
    }
