"""remove election tables and columns

Revision ID: a1b2c3d4e5f6
Revises: 864477aff6a3
Create Date: 2026-05-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = '864477aff6a3'
branch_labels = None
depends_on = None


def upgrade():
    # Drop tables that depended on elections first (foreign keys)
    op.execute("DROP TABLE IF EXISTS results CASCADE")
    op.execute("DROP TABLE IF EXISTS votes CASCADE")
    op.execute("DROP TABLE IF EXISTS user_election_roles CASCADE")
    op.execute("DROP TABLE IF EXISTS elections CASCADE")

    # Remove election-related columns from users
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('participation_points')
        batch_op.drop_column('elections_participated')
        batch_op.drop_column('last_participation_date')

    # Drop the ElectionRole enum type (PostgreSQL only — safe to ignore on SQLite)
    op.execute("DROP TYPE IF EXISTS electionrole")


def downgrade():
    # Restore columns on users
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('participation_points', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('elections_participated', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('last_participation_date', sa.DateTime(), nullable=True))

    # Note: restoring elections/votes tables is not implemented in downgrade.
    # Re-run original migrations from scratch if you need to roll back.
