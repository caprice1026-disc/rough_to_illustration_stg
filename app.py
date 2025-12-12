from __future__ import annotations

from flask import Flask

from config import Config
from extensions import db, login_manager
from views.auth import auth_bp
from views.main import main_bp


def create_app() -> Flask:
    """Flaskアプリケーションを生成し、Blueprintを登録する。"""

    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    with app.app_context():
        db.create_all()

    register_blueprints(app)
    return app


def register_blueprints(app: Flask) -> None:
    """Blueprintをまとめて登録するヘルパー。"""

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
