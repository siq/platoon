"""cached_next col for schedule types

Revision: e888f07ab69
Revises: 1250afd87885
Created: 2013-12-10 16:23:26.510616
"""

revision = 'e888f07ab69'
down_revision = '1250afd87885'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint, CheckConstraint
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('monthly_schedule', 
        Column('cached_next', DateTimeType(timezone=True), nullable=True))
    op.add_column('weekly_schedule', 
        Column('cached_next', DateTimeType(timezone=True), nullable=True))

def downgrade():
    op.drop_column('weekly_schedule', 'cached_next')
    op.drop_column('monthly_schedule', 'cached_next')
