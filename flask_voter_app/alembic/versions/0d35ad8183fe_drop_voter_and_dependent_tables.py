"""Drop voter and dependent tables

Revision ID: 0d35ad8183fe
Revises: 4ee4e7c3064f
Create Date: 2025-03-24 21:52:15.829217

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = '0d35ad8183fe'
down_revision: Union[str, None] = '4ee4e7c3064f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def table_exists(table_name, connection):
    inspector = Inspector.from_engine(connection)
    return inspector.has_table(table_name)
def upgrade():
    connection = op.get_bind()
    # Drop dependent tables first
    if table_exists('result', connection):
        op.drop_table('result')
    if table_exists('vote', connection):
        op.drop_table('vote')

    # Check if the voter table exists before dropping it
    if table_exists('voter', connection):
        op.drop_table('voter')

def downgrade():
    # Recreate tables if needed
    op.create_table(
        'voter',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=50), nullable=False)
    )
    op.create_table(
        'vote',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('voter_id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['voter_id'], ['voter.id'])
    )