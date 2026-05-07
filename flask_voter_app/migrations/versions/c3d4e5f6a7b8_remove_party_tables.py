"""remove party tables and party_id from users

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-05-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c3d4e5f6a7b8'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('users_party_id_fkey', type_='foreignkey')
        batch_op.drop_column('party_id')

    op.drop_table('parties')


def downgrade():
    op.create_table(
        'parties',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('founded_date', sa.DateTime(), nullable=True),
        sa.Column('logo_url', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('party_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('users_party_id_fkey', 'parties', ['party_id'], ['id'])
