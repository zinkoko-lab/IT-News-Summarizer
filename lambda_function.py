from __future__ import annotations

import json

from app import load_settings, run_pipeline


def handler(event, context):
    include_qiita_zenn = True
    if isinstance(event, dict):
        include_qiita_zenn = bool(event.get("include_qiita_zenn", True))

    result = run_pipeline(load_settings(), include_qiita_zenn=include_qiita_zenn)
    return {
        "statusCode": 200,
        "body": json.dumps(result, ensure_ascii=False),
    }
