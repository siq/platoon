"""timezone_issues

Revision: a37cb401b52
Revises: None
Created: 2012-07-26 13:03:49.257873
"""

revision = 'a37cb401b52'
down_revision = None

from alembic import op
from spire.schema.fields import *
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint, CheckConstraint
from sqlalchemy.dialects import postgresql

def upgrade():
    op.alter_column('schedule', 'anchor', type_=DateTimeType(timezone=True))
    op.alter_column('scheduled_task', 'occurrence', type_=DateTimeType(timezone=True))
    op.alter_column('execution', 'started', type_=DateTimeType(timezone=True))
    op.alter_column('execution', 'completed', type_=DateTimeType(timezone=True))

def downgrade():
    op.alter_column('schedule', 'anchor', type_=DateTimeType(timezone=False))
    op.alter_column('scheduled_task', 'occurrence', type_=DateTimeType(timezone=False))
    op.alter_column('execution', 'started', type_=DateTimeType(timezone=False))
    op.alter_column('execution', 'completed', type_=DateTimeType(timezone=False))
