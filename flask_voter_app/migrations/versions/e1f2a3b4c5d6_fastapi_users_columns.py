"""add fastapi-users columns (is_active / is_superuser / is_verified) and tighten email

Phase 4.3.a of the strategic refactor: fastapi-users needs three boolean flags
on the User table and treats email as the canonical login identifier.

Migration steps (idempotent within the upgrade):
    1. ADD COLUMN is_active     BOOLEAN NOT NULL DEFAULT TRUE
       ADD COLUMN is_superuser  BOOLEAN NOT NULL DEFAULT FALSE
       ADD COLUMN is_verified   BOOLEAN NOT NULL DEFAULT TRUE
    2. Backfill is_superuser from the existing `role` text column (Admin → True).
    3. Backfill any NULL emails with `<username>@vote-app.local` so the column
       can be made NOT NULL.
    4. ALTER COLUMN email -> NOT NULL UNIQUE.

The `role` column stays for now (Phase 4.3 keeps backward compat with Flask
side); Phase 4.5 deletes it.

Revision ID: e1f2a3b4c5d6
Revises: c3d4e5f6a7b8
Create Date: 2026-05-25 18:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "e1f2a3b4c5d6"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    # ── 1. Add the three boolean flags (with safe defaults for existing rows) ──
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_active",    sa.Boolean(), nullable=False,
                      server_default=sa.text("1"))
        )
        batch_op.add_column(
            sa.Column("is_superuser", sa.Boolean(), nullable=False,
                      server_default=sa.text("0"))
        )
        batch_op.add_column(
            sa.Column("is_verified",  sa.Boolean(), nullable=False,
                      server_default=sa.text("1"))
        )

    # ── 2. Backfill is_superuser from the legacy role column ─────────────────
    op.execute(sa.text("UPDATE users SET is_superuser = 1 WHERE role = 'Admin'"))

    # ── 3. Backfill missing emails so the NOT NULL alter passes ──────────────
    op.execute(sa.text(
        "UPDATE users "
        "SET email = COALESCE(email, username || '@vote-app.local')"
    ))

    # ── 4. Tighten email constraints (NOT NULL + UNIQUE) ─────────────────────
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column("email",
                              existing_type=sa.String(length=120),
                              nullable=False)
        batch_op.create_unique_constraint("uq_users_email", ["email"])


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("uq_users_email", type_="unique")
        batch_op.alter_column("email",
                              existing_type=sa.String(length=120),
                              nullable=True)
        batch_op.drop_column("is_verified")
        batch_op.drop_column("is_superuser")
        batch_op.drop_column("is_active")
