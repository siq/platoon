from spire.schema import *
from spire.support.logs import LogHelper

from platoon.models.action import *

__all__ = ('Task', 'TaskExecution')

log = LogHelper('platoon')
schema = Schema('platoon')

class TaskExecution(Model):
    """A task execution."""

    class meta:
        constraints = [UniqueConstraint('task_id', 'attempt')]
        schema = schema
        tablename = 'execution'

    id = Identifier()
    task_id = ForeignKey('scheduled_task.task_id', nullable=False, ondelete='CASCADE')
    attempt = Integer(nullable=False)
    status = Enumeration('completed failed')
    started = DateTime(timezone=True)
    completed = DateTime(timezone=True)
    result = Text()

class Task(Model):
    """A queue task."""

    class meta:
        polymorphic_on = 'type'
        schema = schema
        tablename = 'task'

    id = Identifier()
    type = Enumeration('scheduled recurring', nullable=False)
    tag = Text(nullable=False)
    description = Text()
    retry_backoff = Float()
    retry_limit = Integer(nullable=False, default=2)
    retry_timeout = Integer(nullable=False, default=300)
    action_id = ForeignKey('action.id', nullable=False, ondelete='CASCADE')
    failed_action_id = ForeignKey('action.id', ondelete='CASCADE')
    completed_action_id = ForeignKey('action.id', ondelete='CASCADE')

    action = relationship(TaskAction, primaryjoin='TaskAction.id==Task.action_id',
        cascade='all')
    failed_action = relationship(TaskAction, primaryjoin='TaskAction.id==Task.failed_action_id',
        cascade='all')
    completed_action = relationship(TaskAction, primaryjoin='TaskAction.id==Task.completed_action_id',
        cascade='all')
