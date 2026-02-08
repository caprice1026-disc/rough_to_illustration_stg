from __future__ import annotations

import json
import time
from uuid import uuid4

from flask import Flask, current_app, g, jsonify, redirect, request
from flask.cli import with_appcontext
from flask_login import current_user, logout_user
from flask_migrate import upgrade
from flask_wtf.csrf import CSRFError
import click
from pathlib import Path
from werkzeug.middleware.proxy_fix import ProxyFix

from sqlalchemy import inspect

from config import Config
from extensions import csrf, db, login_manager, migrate
from models import User
from views.api import api_bp
from views.spa import spa_bp


def create_app(config_object: object | None = None) -> Flask:
    """Flaskアプリケーションを生成し、Blueprintを登録する。"""

    app = Flask(__name__)
    app.config.from_object(Config)
    if config_object:
        if isinstance(config_object, dict):
            app.config.update(config_object)
        else:
            app.config.from_object(config_object)

    ensure_instance_path(app)
    apply_proxy_fix(app)
    ensure_secret_key(app)
    ensure_database_url(app)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "spa.index"
    register_auth_handlers()
    register_user_status_handlers(app)
    register_security_handlers(app)
    register_request_logging(app)
    register_cli(app)

    register_blueprints(app)
    maybe_auto_migrate(app)
    maybe_auto_init_user(app)
    return app


def apply_proxy_fix(app: Flask) -> None:
    """リバースプロキシ配下で X-Forwarded-* ヘッダーを反映する。"""

    if app.config.get("APP_ENV", "").strip().lower() not in {"production", "staging"}:
        return

    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_port=1,
        x_prefix=1,
    )


def ensure_secret_key(app: Flask) -> None:
    """SECRET_KEY が設定されていない場合は起動を停止する。"""

    secret_key = app.config.get("SECRET_KEY")
    if not secret_key:
        app.logger.critical("SECRET_KEY が未設定です。.env で設定してください。")
        raise RuntimeError("SECRET_KEY が未設定です。.env で設定してください。")


def ensure_instance_path(app: Flask) -> None:
    """SQLite/ローカル保存のために instance パスを確保する。"""

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)


def ensure_database_url(app: Flask) -> None:
    """本番/ステージングでDB設定があることを保証する。"""

    app_env = (app.config.get("APP_ENV") or "").strip().lower()
    if app_env not in {"production", "staging"}:
        return

    database_url = app.config.get("SQLALCHEMY_DATABASE_URI")
    if not database_url:
        message = "データベース未設定です。DATABASE_URL もしくは DB_* を設定してください。"
        app.logger.critical(message)
        raise RuntimeError(message)
    if database_url.startswith("sqlite"):
        message = "本番/ステージングでは SQLite は使用できません。DATABASE_URL か DB_* で MySQL を設定してください。"
        app.logger.critical(message)
        raise RuntimeError(message)


def ensure_initial_user(app: Flask) -> None:
    """環境変数からイニシャルユーザーを作成する。"""

    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        app.logger.info(
            "User table not found. Run 'flask --app app.py db upgrade' or 'flask --app app.py init-db'."
        )
        return

    username = app.config.get("INITIAL_USER_USERNAME")
    email = app.config.get("INITIAL_USER_EMAIL")
    password = app.config.get("INITIAL_USER_PASSWORD")
    if not username or not email or not password:
        app.logger.info("イニシャルユーザーの環境変数が未設定のため作成をスキップしました。")
        return

    existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        if existing_user.role != "admin":
            existing_user.role = "admin"
            db.session.commit()
            app.logger.info("既存のイニシャルユーザーに管理者権限を付与しました。")
        return

    if User.query.first() is not None:
        app.logger.warning("既存ユーザーが存在するためイニシャルユーザーの作成をスキップしました。")
        return

    user = User(username=username, email=email)
    user.set_password(password)
    user.role = "admin"
    db.session.add(user)
    db.session.commit()
    app.logger.info("イニシャルユーザーを作成しました。")


def maybe_auto_migrate(app: Flask) -> None:
    """必要に応じて起動時マイグレーションを実行する。"""

    if not app.config.get("APP_AUTO_MIGRATE"):
        return
    if (app.config.get("APP_ENV") or "").strip().lower() in {"production", "staging"}:
        app.logger.info("APP_AUTO_MIGRATE は production/staging では無視されます。")
        return
    with app.app_context():
        upgrade()
        app.logger.info("起動時マイグレーションが完了しました。")


def maybe_auto_init_user(app: Flask) -> None:
    """必要に応じて起動時に初期ユーザーを作成する。"""

    if not app.config.get("APP_AUTO_INIT_USER"):
        return
    with app.app_context():
        ensure_initial_user(app)


def register_blueprints(app: Flask) -> None:
    """Blueprintをまとめて登録するヘルパー。"""

    app.register_blueprint(api_bp)
    app.register_blueprint(spa_bp)


def register_auth_handlers() -> None:
    """API向けの未認証応答をJSONで返す。"""

    @login_manager.unauthorized_handler
    def unauthorized():  # type: ignore[override]
        if request.path.startswith("/api/"):
            return jsonify({"error": "認証が必要です。"}), 401
        return redirect("/")


def register_user_status_handlers(app: Flask) -> None:
    """無効化ユーザーのセッションを失効させる。"""

    @app.before_request
    def enforce_active_user():
        if not current_user.is_authenticated:
            return None
        if current_user.is_active:
            return None
        logout_user()
        if request.path.startswith("/api/"):
            return jsonify({"error": "アカウントが無効化されています。"}), 403
        return redirect("/")


def register_security_handlers(app: Flask) -> None:
    """APIリクエスト向けのCSRF/Originチェックを登録する。"""

    @app.before_request
    def enforce_api_origin():
        if not request.path.startswith("/api/"):
            return None
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None

        host_url = request.host_url.rstrip("/")
        origin = request.headers.get("Origin")
        referer = request.headers.get("Referer")

        if origin and not origin.startswith(host_url):
            return jsonify({"error": "リクエスト元が不正です。"}), 403
        if not origin and referer and not referer.startswith(host_url):
            return jsonify({"error": "リクエスト元が不正です。"}), 403
        return None

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error: CSRFError):  # type: ignore[override]
        if request.path.startswith("/api/"):
            return jsonify({"error": "CSRFトークンが不正です。"}), 400
        return "CSRFトークンが不正です。", 400


def register_request_logging(app: Flask) -> None:
    """リクエストID付与と構造化ログを設定する。"""

    @app.before_request
    def start_request_timer():
        g.request_id = request.headers.get("X-Request-Id") or uuid4().hex
        g.request_start = time.perf_counter()

    @app.after_request
    def log_request(response):
        start_time = g.get("request_start")
        duration_ms = None
        if isinstance(start_time, (int, float)):
            duration_ms = int((time.perf_counter() - start_time) * 1000)

        user_id = current_user.id if current_user.is_authenticated else None
        payload = {
            "type": "request",
            "request_id": g.get("request_id"),
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "remote_addr": request.headers.get("X-Forwarded-For", request.remote_addr),
        }
        app.logger.info(json.dumps(payload, ensure_ascii=False))
        response.headers["X-Request-Id"] = g.get("request_id", "")
        return response


def register_cli(app: Flask) -> None:
    """DB初期化用のCLIコマンドを登録する。"""

    @app.cli.command("init-db")
    @with_appcontext
    def init_db_command() -> None:
        upgrade()
        ensure_initial_user(current_app)
        click.echo("データベースの初期化が完了しました。")


if __name__ == "__main__":
    # 開発用途: 直接 `python app.py` で起動できるようにする。
    # 本番(Cloud Run/Gunicorn)は `wsgi.py` をエントリポイントとして利用する。
    app = create_app()
    debug_enabled = bool(app.config.get("DEBUG"))
    app.run(debug=debug_enabled)
