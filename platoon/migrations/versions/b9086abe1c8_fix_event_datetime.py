"""fix_event_datetime

Revision: b9086abe1c8
Revises: 2695e2813288
Created: 2012-09-19 17:49:44.907086
"""

revision = 'b9086abe1c8'
down_revision = '2695e2813288'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint, CheckConstraint
from sqlalchemy.dialects import postgresql

def upgrade():
    op.alter_column('event', 'occurrence', type_=DateTimeType(timezone=True))

def downgrade():
    op.alter_column('event', 'occurrence', type_=DateTimeType(timezone=False))
