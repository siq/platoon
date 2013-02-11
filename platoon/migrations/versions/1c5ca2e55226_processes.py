"""processes

Revision: 1c5ca2e55226
Revises: 3035b9805026
Created: 2013-02-11 14:19:42.986280
"""

revision = '1c5ca2e55226'
down_revision = '3035b9805026'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint, CheckConstraint
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table('endpoint',
        Column('id', UUIDType(), nullable=False),
        Column('type', EnumerationType(), nullable=False),
        PrimaryKeyConstraint('id')
    )
    op.create_table('executor',
        Column('id', TokenType(), nullable=False),
        Column('name', TextType(), nullable=True),
        Column('status', EnumerationType(), nullable=False),
        PrimaryKeyConstraint('id')
    )
    op.create_table('http_endpoint',
        Column('endpoint_id', UUIDType(), nullable=False),
        Column('url', TextType(), nullable=False),
        Column('method', TextType(), nullable=False),
        Column('mimetype', TextType(), nullable=False),
        Column('headers', JsonType(), nullable=True),
        Column('info', JsonType(), nullable=True),
        ForeignKeyConstraint(['endpoint_id'], ['endpoint.id'], ),
        PrimaryKeyConstraint('endpoint_id')
    )
    op.create_table('queue',
        Column('id', TokenType(), nullable=False),
        Column('subject', TokenType(), nullable=False),
        Column('name', TextType(), nullable=True),
        Column('status', EnumerationType(), nullable=False),
        Column('endpoint_id', UUIDType(), nullable=True),
        ForeignKeyConstraint(['endpoint_id'], ['endpoint.id'], ),
        PrimaryKeyConstraint('id')
    )
    op.create_table('executor_endpoint',
        Column('id', UUIDType(), nullable=False),
        Column('executor_id', TokenType(), nullable=False),
        Column('endpoint_id', UUIDType(), nullable=False),
        Column('subject', TextType(), nullable=False),
        ForeignKeyConstraint(['endpoint_id'], ['endpoint.id'], ),
        ForeignKeyConstraint(['executor_id'], ['executor.id'], ),
        PrimaryKeyConstraint('id')
    )
    op.create_table('process',
        Column('id', UUIDType(), nullable=False),
        Column('queue_id', TokenType(), nullable=False),
        Column('executor_endpoint_id', UUIDType(), nullable=True),
        Column('tag', TextType(), nullable=False),
        Column('timeout', IntegerType(), nullable=True),
        Column('status', EnumerationType(), nullable=False),
        Column('input', JsonType(), nullable=True),
        Column('output', JsonType(), nullable=True),
        Column('progress', JsonType(), nullable=True),
        Column('started', DateTimeType(timezone=True), nullable=True),
        Column('ended', DateTimeType(timezone=True), nullable=True),
        Column('communicated', DateTimeType(timezone=True), nullable=True),
        ForeignKeyConstraint(['executor_endpoint_id'], ['executor_endpoint.id'], ),
        ForeignKeyConstraint(['queue_id'], ['queue.id'], ),
        PrimaryKeyConstraint('id')
    )
    op.create_table('process_action',
        Column('action_id', UUIDType(), nullable=False),
        Column('process_id', UUIDType(), nullable=False),
        Column('action', EnumerationType(), nullable=False),
        ForeignKeyConstraint(['action_id'], ['action.id'], ),
        ForeignKeyConstraint(['process_id'], ['process.id'], ),
        PrimaryKeyConstraint('action_id')
    )
    op.create_table('process_task',
        Column('id', UUIDType(), nullable=False),
        Column('process_id', UUIDType(), nullable=False),
        Column('task_id', UUIDType(), nullable=False),
        Column('phase', EnumerationType(), nullable=False),
        ForeignKeyConstraint(['process_id'], ['process.id'], ),
        ForeignKeyConstraint(['task_id'], ['scheduled_task.task_id'], ),
        PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('process_task')
    op.drop_table('process_action')
    op.drop_table('process')
    op.drop_table('executor_endpoint')
    op.drop_table('queue')
    op.drop_table('http_endpoint')
    op.drop_table('executor')
    op.drop_table('endpoint')
