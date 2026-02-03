"""初期スキーマを作成する。

リビジョンID: 20260203_01_initial_schema
親リビジョン: なし
作成日時: 2026-02-03 22:05:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# Alembic 用の識別子
revision = "20260203_01_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """初期スキーマを作成する。"""
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("username", sa.String(length=80), nullable=False, unique=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("role IN ('admin', 'user')", name="ck_users_role"),
    )
    op.create_index("ix_users_created_at", "users", ["created_at"], unique=False)

    op.create_table(
        "presets",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("mode", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column(
            "payload_json",
            sa.JSON().with_variant(mysql.JSON(), "mysql"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "mode", "name", name="uq_presets_user_mode_name"),
    )
    op.create_index(
        "ix_presets_user_mode_updated_at",
        "presets",
        ["user_id", "mode", "updated_at"],
        unique=False,
    )

    op.create_table(
        "generations",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("mode", sa.String(length=40), nullable=False),
        sa.Column("aspect_ratio", sa.String(length=16), nullable=True),
        sa.Column("resolution", sa.String(length=16), nullable=True),
        sa.Column("edit_mode", sa.String(length=16), nullable=True),
        sa.Column("model_image", sa.String(length=80), nullable=True),
        sa.Column("model_text", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        sa.Column("error_message", sa.String(length=255), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued','running','succeeded','failed')",
            name="ck_generations_status",
        ),
        sa.CheckConstraint(
            "(edit_mode IS NULL) OR (edit_mode IN ('inpaint','outpaint'))",
            name="ck_generations_edit_mode",
        ),
    )
    op.create_index(
        "ix_generations_user_created_at",
        "generations",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_generations_status_created_at",
        "generations",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "generation_assets",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("generation_id", sa.BigInteger(), sa.ForeignKey("generations.id"), nullable=False),
        sa.Column("storage_backend", sa.String(length=16), nullable=False),
        sa.Column("bucket", sa.String(length=255), nullable=True),
        sa.Column("object_name", sa.String(length=1024), nullable=True),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=True),
        sa.Column("width", sa.BigInteger(), nullable=True),
        sa.Column("height", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "storage_backend IN ('local','gcs')",
            name="ck_generation_assets_storage",
        ),
        sa.CheckConstraint(
            "(storage_backend != 'gcs') OR (bucket IS NOT NULL AND object_name IS NOT NULL)",
            name="ck_generation_assets_gcs_required_fields",
        ),
    )
    op.create_index(
        "ix_generation_assets_generation_id",
        "generation_assets",
        ["generation_id"],
        unique=False,
    )
    op.create_index(
        "ix_generation_assets_sha256",
        "generation_assets",
        ["sha256"],
        unique=False,
    )


def downgrade() -> None:
    """初期スキーマを削除する。"""
    op.drop_index("ix_generation_assets_sha256", table_name="generation_assets")
    op.drop_index("ix_generation_assets_generation_id", table_name="generation_assets")
    op.drop_table("generation_assets")

    op.drop_index("ix_generations_status_created_at", table_name="generations")
    op.drop_index("ix_generations_user_created_at", table_name="generations")
    op.drop_table("generations")

    op.drop_index("ix_presets_user_mode_updated_at", table_name="presets")
    op.drop_table("presets")

    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_table("users")
