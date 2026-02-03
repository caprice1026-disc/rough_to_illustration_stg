from __future__ import annotations

from typing import Optional

from flask import current_app
from flask_login import UserMixin
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Integer,
    JSON,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
    func,
)
from sqlalchemy.dialects.mysql import JSON as MySQLJSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db, login_manager

BIGINT = BigInteger().with_variant(Integer, "sqlite")


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(BIGINT, primary_key=True)
    username = db.Column(String(80), nullable=False, unique=True)
    email = db.Column(String(255), nullable=False, unique=True)

    # パスワードは必ずハッシュで保持（平文禁止）
    password_hash = db.Column(String(255), nullable=False)

    # 権限は文字列で保持（MySQL ENUM は後で辛いので避ける）
    role = db.Column(String(20), nullable=False, default="user")
    is_active = db.Column(Boolean, nullable=False, default=True)

    created_at = db.Column(DateTime, nullable=False, server_default=func.now())
    updated_at = db.Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    last_login_at = db.Column(DateTime, nullable=True)

    presets = relationship("Preset", back_populates="user", cascade="all, delete-orphan")
    generations = relationship("Generation", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'user')", name="ck_users_role"),
        Index("ix_users_created_at", "created_at"),
    )

    def set_password(self, raw_password: str) -> None:
        """平文パスワードをハッシュ化して保存する。"""

        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """入力パスワードと保存済みハッシュを照合する。"""

        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_initial_user(self) -> bool:
        """初期ユーザーかどうかを判定する。"""

        username = current_app.config.get("INITIAL_USER_USERNAME")
        email = current_app.config.get("INITIAL_USER_EMAIL")
        if not username or not email:
            return False
        return self.username == username and self.email == email


class Preset(db.Model):
    """
    統合プリセットテーブル。
    mode ごとに payload_json の中身が変わる前提。
    """
    __tablename__ = "presets"

    id = db.Column(BIGINT, primary_key=True)
    user_id = db.Column(BIGINT, ForeignKey("users.id"), nullable=False)

    # 例: rough_with_instructions / reference_style_colorize / inpaint_outpaint
    mode = db.Column(String(40), nullable=False)

    name = db.Column(String(80), nullable=False)

    # モード別の入力を格納する（例: color_instruction, pose_instruction, edit_mode 等）
    # MySQL 本番/SQLite ローカルの両対応
    payload_json = db.Column(
        MutableDict.as_mutable(JSON().with_variant(MySQLJSON, "mysql")),
        nullable=False,
        default=dict,
    )

    # DB 側時刻を優先（多重プロセス・タイムゾーン差分を吸収）
    created_at = db.Column(DateTime, nullable=False, server_default=func.now())
    updated_at = db.Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="presets")

    __table_args__ = (
        # 同一ユーザー＋同一モードで同名プリセットを禁止（運用がラク）
        UniqueConstraint("user_id", "mode", "name", name="uq_presets_user_mode_name"),
        Index("ix_presets_user_mode_updated_at", "user_id", "mode", "updated_at"),
    )


class Generation(db.Model):
    """
    生成の“イベント”を表す履歴本体。
    入力画像は保存しない前提なので、メタ情報のみを保持。
    """
    __tablename__ = "generations"

    id = db.Column(BIGINT, primary_key=True)
    user_id = db.Column(BIGINT, ForeignKey("users.id"), nullable=False)

    mode = db.Column(String(40), nullable=False)

    # UIの "auto" は NULL に寄せると扱いやすい
    aspect_ratio = db.Column(String(16), nullable=True)
    resolution = db.Column(String(16), nullable=True)

    # inpaint/outpaint の場合のみ設定（それ以外は NULL）
    edit_mode = db.Column(String(16), nullable=True)

    # 使ったモデル名を記録（後で調査に効く）
    model_image = db.Column(String(80), nullable=True)
    model_text = db.Column(String(80), nullable=True)

    # 状態管理（同期APIでも future-proof）
    status = db.Column(String(16), nullable=False, default="queued")
    started_at = db.Column(DateTime, nullable=True)
    finished_at = db.Column(DateTime, nullable=True)
    duration_ms = db.Column(BIGINT, nullable=True)

    # プロンプトは保存しない要件なので、ここには持たない
    # エラーは残す
    error_code = db.Column(String(40), nullable=True)
    error_message = db.Column(String(255), nullable=True)
    error_detail = db.Column(Text, nullable=True)

    # 入力画像のフィンガープリント（任意：保存しないが同一入力の識別に使える）
    input_fingerprint = db.Column(String(64), nullable=True)

    created_at = db.Column(DateTime, nullable=False, server_default=func.now())
    updated_at = db.Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="generations")
    assets = relationship("GenerationAsset", back_populates="generation", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status IN ('queued','running','succeeded','failed')", name="ck_generations_status"),
        CheckConstraint(
            "(edit_mode IS NULL) OR (edit_mode IN ('inpaint','outpaint'))",
            name="ck_generations_edit_mode",
        ),
        Index("ix_generations_user_created_at", "user_id", "created_at"),
        Index("ix_generations_status_created_at", "status", "created_at"),
    )


class GenerationAsset(db.Model):
    """
    生成物の“実体”（GCSオブジェクト等）を表す。
    将来のサムネ/複数候補/削除にも耐えるため、結果画像は assets に分離する。
    """
    __tablename__ = "generation_assets"

    id = db.Column(BIGINT, primary_key=True)
    generation_id = db.Column(BIGINT, ForeignKey("generations.id"), nullable=False)

    # local / gcs
    storage_backend = db.Column(String(16), nullable=False, default="gcs")

    # GCSの場合：bucket と object_name を持つ（署名URLは都度生成する想定）
    bucket = db.Column(String(255), nullable=True)
    object_name = db.Column(String(1024), nullable=True)

    mime_type = db.Column(String(64), nullable=False, default="image/png")
    byte_size = db.Column(BIGINT, nullable=True)
    width = db.Column(BIGINT, nullable=True)
    height = db.Column(BIGINT, nullable=True)
    sha256 = db.Column(String(64), nullable=True)

    # 将来の削除に備えたソフトデリート
    deleted_at = db.Column(DateTime, nullable=True)

    created_at = db.Column(DateTime, nullable=False, server_default=func.now())

    generation = relationship("Generation", back_populates="assets")

    __table_args__ = (
        CheckConstraint("storage_backend IN ('local','gcs')", name="ck_generation_assets_storage"),
        CheckConstraint(
            "(storage_backend != 'gcs') OR (bucket IS NOT NULL AND object_name IS NOT NULL)",
            name="ck_generation_assets_gcs_required_fields",
        ),
        Index("ix_generation_assets_generation_id", "generation_id"),
        Index("ix_generation_assets_sha256", "sha256"),
    )


class ChatSession(db.Model):
    """チャットセッションを表すモデル。"""

    __tablename__ = "chat_sessions"

    id = db.Column(BIGINT, primary_key=True)
    user_id = db.Column(BIGINT, ForeignKey("users.id"), nullable=False)
    title = db.Column(String(120), nullable=False)
    created_at = db.Column(DateTime, nullable=False, server_default=func.now())
    updated_at = db.Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )

    __table_args__ = (
        Index("ix_chat_sessions_user_updated_at", "user_id", "updated_at"),
    )


class ChatMessage(db.Model):
    """チャット内のメッセージを表すモデル。"""

    __tablename__ = "chat_messages"

    id = db.Column(BIGINT, primary_key=True)
    session_id = db.Column(BIGINT, ForeignKey("chat_sessions.id"), nullable=False)
    role = db.Column(String(20), nullable=False)
    text = db.Column(Text, nullable=True)
    mode_id = db.Column(String(80), nullable=True)
    created_at = db.Column(DateTime, nullable=False, server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")
    attachments = relationship("ChatAttachment", back_populates="message", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("role IN ('user','assistant','system')", name="ck_chat_messages_role"),
        Index("ix_chat_messages_session_created_at", "session_id", "created_at"),
    )


class ChatAttachment(db.Model):
    """チャットメッセージに紐づく画像ファイル。"""

    __tablename__ = "chat_attachments"

    id = db.Column(BIGINT, primary_key=True)
    message_id = db.Column(BIGINT, ForeignKey("chat_messages.id"), nullable=False)
    kind = db.Column(String(40), nullable=False, default="image")

    storage_backend = db.Column(String(16), nullable=False, default="gcs")
    bucket = db.Column(String(255), nullable=True)
    object_name = db.Column(String(1024), nullable=True)

    mime_type = db.Column(String(64), nullable=False, default="image/png")
    byte_size = db.Column(BIGINT, nullable=True)
    width = db.Column(BIGINT, nullable=True)
    height = db.Column(BIGINT, nullable=True)
    sha256 = db.Column(String(64), nullable=True)
    created_at = db.Column(DateTime, nullable=False, server_default=func.now())

    message = relationship("ChatMessage", back_populates="attachments")

    __table_args__ = (
        CheckConstraint("storage_backend IN ('local','gcs')", name="ck_chat_attachments_storage"),
        CheckConstraint(
            "(storage_backend != 'gcs') OR (bucket IS NOT NULL AND object_name IS NOT NULL)",
            name="ck_chat_attachments_gcs_required_fields",
        ),
        Index("ix_chat_attachments_message_id", "message_id"),
    )


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    """ログインセッションからユーザーを復元する。"""

    if not user_id:
        return None
    return User.query.get(int(user_id))
