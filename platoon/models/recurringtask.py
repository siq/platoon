from datetime import datetime, timedelta

from scheme import UTC, current_timestamp
from spire.schema import *
from spire.support.logs import LogHelper

from platoon.constants import *
from platoon.models.action import TaskAction
from platoon.models.task import Task

__all__ = ('RecurringTask',)

log = LogHelper('platoon')
schema = Schema('platoon')

class RecurringTask(Task):
    """A recurring task."""

    class meta:
        polymorphic_identity = 'recurring'
        schema = schema
        tablename = 'recurring_task'

    task_id = ForeignKey('task.id', nullable=False, primary_key=True, ondelete='CASCADE')
    status = Enumeration('active inactive', nullable=False, default='active')
    schedule_id = ForeignKey('schedule.id', nullable=False)

    schedule = relationship('Schedule')

    @classmethod
    def create(cls, session, tag, action, schedule_id, status='active',
            failed_action=None, completed_action=None, description=None,
            retry_backoff=None, retry_limit=2, retry_timeout=300, id=None):

        task = RecurringTask(tag=tag, status=status, description=description,
            schedule_id=schedule_id, retry_backoff=retry_backoff,
            retry_limit=retry_limit, retry_timeout=retry_timeout, id=id)

        task.action = TaskAction.polymorphic_create(action)
        if failed_action:
            task.failed_action = TaskAction.polymorphic_create(failed_action)
        if completed_action:
            task.completed_action = TaskAction.polymorphic_create(completed_action)

        session.add(task)
        if status == 'active':
            session.flush()
            task.reschedule(session, datetime.now(UTC))
        return task

    def has_pending_task(self, session):
        from platoon.models.scheduledtask import ScheduledTask
        query = session.query(ScheduledTask).filter_by(parent_id=self.id, status='pending')
        return query.count() >= 1

    def reschedule(self, session, occurrence=None):
        from platoon.models.scheduledtask import ScheduledTask
        if self.status != 'active':
            return
        if occurrence is None:
            occurrence = current_timestamp()

        query = session.query(ScheduledTask).filter_by(status='pending', parent_id=self.id)
        if query.count() > 0:
            return

        occurrence = self.schedule.next(occurrence)
        task = ScheduledTask.spawn(self, occurrence, parent_id=self.id)

        session.add(task)
        return task

    def update(self, session, action=None, failed_action=None, completed_action=None, **params):
        self.update_with_mapping(params)
        if action:
            self.action.update_with_mapping(action)
        if failed_action:
            if self.failed_action:
                self.failed_action.update_with_mapping(failed_action)
            else:
                self.failed_action = TaskAction.polymorphic_create(failed_action)
        if completed_action:
            if self.completed_action:
                self.completed_action.update_with_mapping(completed_action)
            else:
                self.completed_action = TaskAction.polymorphic_create(completed_action)

        session.flush()
        if self.status == 'active' and not self.has_pending_task(session):
            self.reschedule(session, datetime.now(UTC))
