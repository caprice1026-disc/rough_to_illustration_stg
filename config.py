from __future__ import annotations

import os

from dotenv import load_dotenv

# .env を読み込んで環境変数を初期化する
load_dotenv()


class Config:
    """Flaskアプリの設定値をまとめたクラス。"""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
