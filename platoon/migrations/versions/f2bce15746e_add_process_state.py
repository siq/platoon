"""add_process_state

Revision: f2bce15746e
Revises: 1c5ca2e55226
Created: 2013-02-14 14:28:05.909297
"""

revision = 'f2bce15746e'
down_revision = '1c5ca2e55226'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint, CheckConstraint
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('process', Column('state', JsonType(), nullable=True))

def downgrade():
    op.drop_column('process', 'state')
