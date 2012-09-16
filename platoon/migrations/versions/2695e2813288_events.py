"""events

Revision: 2695e2813288
Revises: 2cedcf202ceb
Created: 2012-09-16 12:35:50.265663
"""

revision = '2695e2813288'
down_revision = '2cedcf202ceb'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint, CheckConstraint
from sqlalchemy.dialects import postgresql

def upgrade():
    op.execute("create execution if not exists hstore")
    op.create_table('event',
        Column('id', UUIDType(), nullable=False),
        Column('topic', TokenType(), nullable=False),
        Column('aspects', HstoreType(), nullable=True),
        Column('status', EnumerationType(), nullable=False),
        Column('occurrence', DateTimeType(), nullable=True),
        PrimaryKeyConstraint('id')
    )
    op.create_table('internal_action',
        Column('action_id', UUIDType(), nullable=False),
        Column('purpose', EnumerationType(), nullable=False),
        ForeignKeyConstraint(['action_id'], ['action.id'], ),
        PrimaryKeyConstraint('action_id')
    )
    op.create_table('subscribed_task',
        Column('task_id', UUIDType(), nullable=False),
        Column('topic', TokenType(), nullable=False),
        Column('aspects', HstoreType(), nullable=True),
        Column('activation_limit', IntegerType(), nullable=True),
        Column('activations', IntegerType(), nullable=False),
        ForeignKeyConstraint(['task_id'], ['task.id'], ),
        PrimaryKeyConstraint('task_id')
    )
    op.execute("create index subscribed_task_aspects_idx on subscribed_task using gist (aspects)")
    op.add_column('http_request_action', Column('injections', SerializedType(), nullable=True))
    op.add_column('scheduled_task', Column('parameters', SerializedType(), nullable=True))

def downgrade():
    op.drop_column('scheduled_task', 'parameters')
    op.drop_column('http_request_action', 'injections')
    op.execute("drop index subscribed_task_aspects_idx")
    op.drop_table('subscribed_task')
    op.drop_table('internal_action')
    op.drop_table('event')
