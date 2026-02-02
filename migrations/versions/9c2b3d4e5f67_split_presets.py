"""split presets by mode

Revision ID: 9c2b3d4e5f67
Revises: 6f4a8c7d9b12
Create Date: 2026-01-31 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "9c2b3d4e5f67"
down_revision = "6f4a8c7d9b12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rough_presets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("color_instruction", sa.String(length=1000), nullable=False),
        sa.Column("pose_instruction", sa.String(length=1000), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "reference_presets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("reference_instruction", sa.String(length=1000), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "edit_presets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("edit_instruction", sa.String(length=1000), nullable=False),
        sa.Column(
            "edit_mode",
            sa.String(length=20),
            server_default=sa.text("'inpaint'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
    )

    op.execute(
        """
        INSERT INTO rough_presets (user_id, name, color_instruction, pose_instruction, created_at)
        SELECT user_id, name, color_instruction, pose_instruction, created_at
        FROM illustration_presets
        """
    )


def downgrade() -> None:
    op.drop_table("edit_presets")
    op.drop_table("reference_presets")
    op.drop_table("rough_presets")
