from __future__ import annotations

import json

from app import load_settings, run_pipeline


if __name__ == "__main__":
    result = run_pipeline(load_settings(), include_qiita_zenn=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))
