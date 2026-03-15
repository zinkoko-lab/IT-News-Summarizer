from __future__ import annotations

from app import load_settings, run_pipeline


def run(request):
    include_qiita_zenn = True
    if request and request.args and "include_qiita_zenn" in request.args:
        include_qiita_zenn = request.args.get("include_qiita_zenn", "true").lower() == "true"

    result = run_pipeline(load_settings(), include_qiita_zenn=include_qiita_zenn)
    return result, 200
