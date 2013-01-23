"""add_created_and_timeout

Revision: 3035b9805026
Revises: b9086abe1c8
Created: 2013-01-23 11:17:07.701154
"""

revision = '3035b9805026'
down_revision = 'b9086abe1c8'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint, CheckConstraint
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('task', Column('created', DateTimeType(timezone=True), nullable=True))
    op.execute("update task set created = current_timestamp")
    op.alter_column('task', 'created', nullable=False)

    op.add_column('subscribed_task', Column('activated', DateTimeType(timezone=True), nullable=True))
    op.add_column('subscribed_task', Column('timeout', IntegerType(), nullable=True))

def downgrade():
    op.drop_column('task', 'created')
    op.drop_column('subscribed_task', 'activated')
    op.drop_column('subscribed_task', 'timeout')
