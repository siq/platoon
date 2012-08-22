"""add_cascades

Revision: 2cedcf202ceb
Revises: a37cb401b52
Created: 2012-08-21 20:45:09.304167
"""

revision = '2cedcf202ceb'
down_revision = 'a37cb401b52'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint, CheckConstraint
from sqlalchemy.dialects import postgresql

def upgrade():
    op.drop_constraint('execution_task_id_fkey', 'execution')
    op.create_foreign_key('execution_task_id_fkey', 'execution', 'scheduled_task',
        ['task_id'], ['task_id'], ondelete='CASCADE')

    op.drop_constraint('http_request_action_action_id_fkey', 'http_request_action')
    op.create_foreign_key('http_request_action_action_id_fkey', 'http_request_action', 'action',
        ['action_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('task_action_id_fkey', 'task')
    op.create_foreign_key('task_action_id_fkey', 'task', 'action',
        ['action_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('task_completed_action_id_fkey', 'task')
    op.create_foreign_key('task_completed_action_id_fkey', 'task', 'action',
        ['completed_action_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('task_failed_action_id_fkey', 'task')
    op.create_foreign_key('task_failed_action_id_fkey', 'task', 'action',
        ['failed_action_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('scheduled_task_parent_id_fkey', 'scheduled_task')
    op.create_foreign_key('scheduled_task_parent_id_fkey', 'scheduled_task', 'recurring_task',
        ['parent_id'], ['task_id'], ondelete='CASCADE')

    op.drop_constraint('scheduled_task_task_id_fkey', 'scheduled_task')
    op.create_foreign_key('scheduled_task_task_id_fkey', 'scheduled_task', 'task',
        ['task_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('recurring_task_task_id_fkey', 'recurring_task')
    op.create_foreign_key('recurring_task_task_id_fkey', 'recurring_task', 'task',
        ['task_id'], ['id'], ondelete='CASCADE')

def downgrade():
    op.drop_constraint('execution_task_id_fkey', 'execution')
    op.create_foreign_key('execution_task_id_fkey', 'execution', 'scheduled_task',
        ['task_id'], ['task_id'])

    op.drop_constraint('http_request_action_action_id_fkey', 'http_request_action')
    op.create_foreign_key('http_request_action_action_id_fkey', 'http_request_action', 'action',
        ['action_id'], ['id'])

    op.drop_constraint('task_action_id_fkey', 'task')
    op.create_foreign_key('task_action_id_fkey', 'task', 'action',
        ['action_id'], ['id'])

    op.drop_constraint('task_completed_action_id_fkey', 'task')
    op.create_foreign_key('task_completed_action_id_fkey', 'task', 'action',
        ['completed_action_id'], ['id'])

    op.drop_constraint('task_failed_action_id_fkey', 'task')
    op.create_foreign_key('task_failed_action_id_fkey', 'task', 'action',
        ['failed_action_id'], ['id'])

    op.drop_constraint('scheduled_task_parent_id_fkey', 'scheduled_task')
    op.create_foreign_key('scheduled_task_parent_id_fkey', 'scheduled_task', 'recurring_task',
        ['parent_id'], ['task_id'])

    op.drop_constraint('scheduled_task_task_id_fkey', 'scheduled_task')
    op.create_foreign_key('scheduled_task_task_id_fkey', 'scheduled_task', 'task',
        ['task_id'], ['id'])

    op.drop_constraint('recurring_task_task_id_fkey', 'recurring_task')
    op.create_foreign_key('recurring_task_task_id_fkey', 'recurring_task', 'task',
        ['task_id'], ['id'])
