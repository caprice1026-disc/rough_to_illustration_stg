from __future__ import annotations

from flask import Flask, request

from config import Config
from extensions import db, login_manager
from models import User
from services.modes import (
    ALL_MODES,
    MODE_CHAT,
    MODE_INPAINT_OUTPAINT,
    MODE_REFERENCE_STYLE_COLORIZE,
    MODE_ROUGH_WITH_INSTRUCTIONS,
    normalize_mode_id,
)
from views.auth import auth_bp
from views.chat import chat_bp
from views.main import main_bp


def create_app(config_object: object | None = None) -> Flask:
    """Flaskアプリケーションを生成し、Blueprintを登録する。"""

    app = Flask(__name__)
    app.config.from_object(Config)
    if config_object:
        if isinstance(config_object, dict):
            app.config.update(config_object)
        else:
            app.config.from_object(config_object)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    with app.app_context():
        db.create_all()
        ensure_initial_user(app)

    register_blueprints(app)
    register_context_processors(app)
    return app


def ensure_initial_user(app: Flask) -> None:
    """環境変数からイニシャルユーザーを作成する。"""

    username = app.config.get("INITIAL_USER_USERNAME")
    email = app.config.get("INITIAL_USER_EMAIL")
    password = app.config.get("INITIAL_USER_PASSWORD")
    if not username or not email or not password:
        app.logger.info("イニシャルユーザーの環境変数が未設定のため作成をスキップしました。")
        return

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return

    if User.query.first() is not None:
        app.logger.warning("既存ユーザーが存在するためイニシャルユーザーの作成をスキップしました。")
        return

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    app.logger.info("イニシャルユーザーを作成しました。")


def register_blueprints(app: Flask) -> None:
    """Blueprintをまとめて登録するヘルパー。"""

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(main_bp)


def register_context_processors(app: Flask) -> None:
    """共通で利用するテンプレート変数を登録する。"""

    endpoint_mode_map = {
        "main.generate_rough": MODE_ROUGH_WITH_INSTRUCTIONS.id,
        "main.generate_reference": MODE_REFERENCE_STYLE_COLORIZE.id,
        "main.generate_edit": MODE_INPAINT_OUTPAINT.id,
        "chat.index": MODE_CHAT.id,
    }

    @app.context_processor
    def inject_mode_context() -> dict[str, object]:
        endpoint = request.endpoint
        current_mode: str | None = None

        if endpoint == "main.mode_select":
            current_mode = normalize_mode_id(request.args.get("mode"))
        elif endpoint in endpoint_mode_map:
            current_mode = endpoint_mode_map[endpoint]

        current_mode_label = None
        if current_mode:
            current_mode_label = next(
                (mode.label for mode in ALL_MODES if mode.id == current_mode),
                None,
            )

        return {
            "modes": ALL_MODES,
            "current_mode": current_mode,
            "current_mode_label": current_mode_label,
        }


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
