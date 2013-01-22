from spire.schema import *
from spire.support.logs import LogHelper

from platoon.constants import *
from platoon.models.action import TaskAction
from platoon.models.scheduledtask import ScheduledTask
from platoon.models.task import Task

__all__ = ('SubscribedTask',)

log = LogHelper('platoon')
schema = Schema('platoon')

class SubscribedTask(Task):
    """A subscribed task."""

    class meta:
        polymorphic_identity = 'subscribed'
        schema = schema
        tablename = 'subscribed_task'

    task_id = ForeignKey('task.id', nullable=False, primary_key=True, ondelete='CASCADE')
    topic = Token(nullable=False)
    aspects = Hstore()
    activation_limit = Integer(minimum=1)
    activations = Integer(nullable=False, default=0)

    def activate(self, session, description):
        limit = self.activation_limit
        if limit is not None and self.activations > limit:
            return

        task = ScheduledTask.spawn(self, parameters={'event': description})
        session.add(task)

        self.activations += 1
        return task

    @classmethod
    def create(cls, session, tag, action, topic, aspects=None, activation_limit=None,
            failed_action=None, completed_action=None, description=None,
            retry_backoff=None, retry_limit=2, retry_timeout=300, id=None):

        task = SubscribedTask(id=id, tag=tag, description=description, topic=topic,
            aspects=aspects, activation_limit=activation_limit, retry_backoff=retry_backoff,
            retry_limit=retry_limit, retry_timeout=retry_timeout)

        task.action = TaskAction.polymorphic_create(action)
        if failed_action:
            task.failed_action = TaskAction.polymorphic_create(failed_action)
        if completed_action:
            task.completed_action = TaskAction.polymorphic_create(completed_action)

        session.add(task)
        return task

SubscribedTaskAspectsIndex = Index('subscribed_task_aspects_idx', SubscribedTask.aspects,
    postgresql_using='gist')
