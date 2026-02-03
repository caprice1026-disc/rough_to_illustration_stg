"""チャット関連テーブルを追加する。

リビジョンID: 20260203_02_add_chat_tables
親リビジョン: 20260203_01_initial_schema
作成日時: 2026-02-03 23:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

# Alembic 用の識別子
revision = "20260203_02_add_chat_tables"
down_revision = "20260203_01_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """チャット関連テーブルを作成する。"""
    op.create_table(
        "chat_sessions",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("user_id", BIGINT, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_chat_sessions_user_updated_at",
        "chat_sessions",
        ["user_id", "updated_at"],
        unique=False,
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("session_id", BIGINT, sa.ForeignKey("chat_sessions.id"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("mode_id", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('user','assistant','system')", name="ck_chat_messages_role"),
    )
    op.create_index(
        "ix_chat_messages_session_created_at",
        "chat_messages",
        ["session_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "chat_attachments",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("message_id", BIGINT, sa.ForeignKey("chat_messages.id"), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("storage_backend", sa.String(length=16), nullable=False),
        sa.Column("bucket", sa.String(length=255), nullable=True),
        sa.Column("object_name", sa.String(length=1024), nullable=True),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("byte_size", BIGINT, nullable=True),
        sa.Column("width", BIGINT, nullable=True),
        sa.Column("height", BIGINT, nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("storage_backend IN ('local','gcs')", name="ck_chat_attachments_storage"),
        sa.CheckConstraint(
            "(storage_backend != 'gcs') OR (bucket IS NOT NULL AND object_name IS NOT NULL)",
            name="ck_chat_attachments_gcs_required_fields",
        ),
    )
    op.create_index(
        "ix_chat_attachments_message_id",
        "chat_attachments",
        ["message_id"],
        unique=False,
    )


def downgrade() -> None:
    """チャット関連テーブルを削除する。"""
    op.drop_index("ix_chat_attachments_message_id", table_name="chat_attachments")
    op.drop_table("chat_attachments")

    op.drop_index("ix_chat_messages_session_created_at", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("ix_chat_sessions_user_updated_at", table_name="chat_sessions")
    op.drop_table("chat_sessions")
