"""本番用WSGIエントリポイント。

Cloud Run / Gunicorn からは本ファイルの `app` を参照して起動する。
（例: `gunicorn wsgi:app`）

テストでは `app.py` の `create_app()` を直接呼び出し、import時の副作用を避ける。
"""

from __future__ import annotations

from flask import Flask

from app import create_app


app: Flask = create_app()


if __name__ == "__main__":
    # 手元検証用: `python wsgi.py`
    debug_enabled = bool(app.config.get("DEBUG"))
    app.run(debug=debug_enabled)

