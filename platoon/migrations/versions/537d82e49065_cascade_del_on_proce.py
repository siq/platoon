"""cascade_del_on_process_task_id_fk

Revision: 537d82e49065
Revises: e888f07ab69
Created: 2016-02-03 19:52:51.400990
"""

revision = '537d82e49065'
down_revision = 'e888f07ab69'

from alembic import op

def upgrade():
    op.drop_constraint('process_task_task_id_fkey', 'process_task', 'foreignkey')

    op.create_foreign_key(
        'process_task_task_id_fkey', 'process_task', 'scheduled_task', 
        ['task_id'], ['task_id'], ondelete='CASCADE')

def downgrade():
    op.drop_constraint('process_task_task_id_fkey', 'process_task', 'foreignkey')

    op.create_foreign_key(
        'process_task_task_id_fkey', 'process_task', 'scheduled_task',
        ['task_id'], ['task_id'])
