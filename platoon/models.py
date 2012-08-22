from datetime import datetime, timedelta
from httplib import HTTPConnection
from traceback import format_exc
from urlparse import urlparse

from scheme import UTC
from spire.schema import *
from spire.support.logs import LogHelper

COMPLETED = 'completed'
FAILED = 'failed'
RETRY = 'retry'

PARTIAL = 206

log = LogHelper('platoon')
schema = Schema('platoon')

class Action(Model):
    """A task action."""

    class meta:
        polymorphic_on = 'type'
        schema = schema
        tablename = 'action'

    id = Identifier()
    type = Enumeration('http-request test', nullable=False)

class TestAction(Action):
    """A test action."""

    class meta:
        polymorphic_identity = 'test'
        schema = schema
        tablename = 'test_action'

    action_id = ForeignKey('action.id', nullable=False, primary_key=True)
    status = Enumeration('complete fail exception', nullable=False)
    result = Text()

    def execute(self):
        if self.status == 'exception':
            raise Exception('test exception')
        elif self.status == 'complete':
            return COMPLETED, self.result
        else:
            return FAILED, self.result

class HttpRequestAction(Action):
    """An http request action."""

    class meta:
        polymorphic_identity = 'http-request'
        schema = schema
        tablename = 'http_request_action'

    action_id = ForeignKey('action.id', nullable=False, primary_key=True, ondelete='CASCADE')
    url = Text(nullable=False)
    method = Enumeration('DELETE GET HEAD OPTIONS POST PUT TASK', nullable=False)
    mimetype = Text()
    data = Text()
    headers = Serialized()
    timeout = Integer()

    def execute(self):
        scheme, host, path = urlparse(self.url)[:3]
        connection = HTTPConnection(host=host, timeout=self.timeout)

        body = self.data
        if body and self.method == 'GET':
            path = '%s/%s' % (path, body)
            body = None

        headers = self.headers or {}
        if 'Content-Type' not in headers and self.mimetype:
            headers['Content-Type'] = self.mimetype

        try:
            connection.request(self.method, path, body, headers)
        except Exception:
            raise

        response = connection.getresponse()
        if response.status == PARTIAL:
            status = RETRY
        elif 200 <= response.status <= 299:
            status = COMPLETED
        else:
            status = FAILED

        return status, self._dump_http_response(response)

    def _dump_http_response(self, response):
        lines = ['%s %s' % (response.status, response.reason)]
        for header, value in response.getheaders():
            lines.append('%s: %s' % (header, value))

        content = response.read()
        if content:
            lines.extend(['', content])
        return '\n'.join(lines)

class Schedule(Model):
    """A task schedule."""

    class meta:
        schema = schema
        tablename = 'schedule'

    id = Identifier()
    name = Text(unique=True)
    schedule = Enumeration('fixed', nullable=False)
    anchor = DateTime(nullable=False, timezone=True)
    interval = Integer(nullable=False)

    def next(self, occurrence):
        occurrence = self._next_occurrence(occurrence)

        now = datetime.now(UTC)
        if occurrence >= now:
            return occurrence
        else:
            return self._next_occurrence(now)

    def _next_occurrence(self, occurrence):
        schedule = self.schedule
        if schedule == 'fixed':
            return self._next_fixed(occurrence)

    def _next_fixed(self, occurrence):
        occurrence = occurrence + timedelta(seconds=self.interval)
        if occurrence >= self.anchor:
            return occurrence
        else:
            return self.anchor

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

    action = relationship('Action', primaryjoin='Action.id==Task.action_id',
        cascade='all')
    failed_action = relationship('Action', primaryjoin='Action.id==Task.failed_action_id',
        cascade='all')
    completed_action = relationship('Action', primaryjoin='Action.id==Task.completed_action_id',
        cascade='all')

class ScheduledTask(Task):
    """A scheduled task."""

    class meta:
        polymorphic_identity = 'scheduled'
        schema = schema
        tablename = 'scheduled_task'

    task_id = ForeignKey('task.id', nullable=False, primary_key=True, ondelete='CASCADE')
    status = Enumeration('pending executing retrying aborted completed failed',
        nullable=False, default='pending')
    occurrence = DateTime(nullable=False, timezone=True)
    parent_id = ForeignKey('recurring_task.task_id', ondelete='CASCADE')

    parent = relationship('RecurringTask', primaryjoin='RecurringTask.task_id==ScheduledTask.parent_id',
        cascade='all')
    executions = relationship('Execution', backref='task', order_by='Execution.attempt',
        cascade='all,delete-orphan', passive_deletes=True)

    @classmethod
    def create(cls, session, tag, action, status='pending', occurrence=None,
            failed_action=None, completed_action=None, description=None,
            retry_backoff=None, retry_limit=2, retry_timeout=300):

        occurrence = occurrence or datetime.now(UTC)
        task = ScheduledTask(tag=tag, status=status, description=description,
            occurrence=occurrence, retry_backoff=retry_backoff,
            retry_limit=retry_limit, retry_timeout=retry_timeout)

        task.action = Action.polymorphic_create(action)
        if failed_action:
            task.failed_action = Action.polymorphic_create(failed_action)
        if completed_action:
            task.completed_action = Action.polymorphic_create(completed_action)

        session.add(task)
        return task

    def execute(self, session):
        parent = None
        if self.parent_id:
            parent = session.query(RecurringTask).with_lockmode('update').get(self.parent_id)

        execution = Execution(task_id=self.id, attempt=len(self.executions) + 1)
        session.add(execution)

        execution.started = datetime.now(UTC)
        try:
            status, execution.result = self.action.execute()
        except Exception, exception:
            status = FAILED
            execution.result = format_exc()

        execution.completed = datetime.now(UTC)
        if status == COMPLETED:
            self.status = execution.status = 'completed'
            log('info', '%s completed (attempt %d)', repr(self), execution.attempt)
            log('debug', 'result for %s:\n%s', repr(self), execution.result)
            if self.completed_action_id:
                session.add(Task(tag='%s-completed' % self.tag, occurrence=datetime.now(UTC),
                    action_id=self.completed_action_id))
        elif execution.attempt == (self.retry_limit + 1):
            self.status = execution.status = 'failed'
            log('error', '%s failed (attempt %d), aborting', repr(self), execution.attempt)
            log('debug', 'result for %s:\n%s', repr(self), execution.result)
            if self.failed_action_id:
                session.add(Task(tag='%s-failed' % self.tag, occurrence=datetime.now(UTC),
                    action_id=self.failed_action_id))
        else:
            execution.status = 'failed'
            self.status = 'retrying'
            self.occurrence = self._calculate_retry(execution)
            if status == FAILED:
                log('warning', '%s failed (attempt %d), retrying', repr(self), execution.attempt)
            else:
                log('info', '%s not yet complete (attempt %s), retrying',
                    repr(self), execution.attempt)
            log('debug', 'result for %s:\n%s', repr(self), execution.result)

        if parent:
            parent.reschedule(session, self.occurrence)

    def update(self, session, data):
        raise NotImplemented()

    def _calculate_retry(self, execution):
        timeout = self.retry_timeout
        if self.retry_backoff is not None:
            timeout *= (self.retry_backoff ** execution.attempt)
        return datetime.now(UTC) + timedelta(seconds=timeout)

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

        task.action = Action.polymorphic_create(action)
        if failed_action:
            task.failed_action = Action.polymorphic_create(failed_action)
        if completed_action:
            task.completed_action = Action.polymorphic_create(completed_action)

        session.add(task)
        if status == 'active':
            session.flush()
            task.reschedule(session, datetime.now(UTC))
        return task

    def has_pending_task(self, session):
        query = session.query(ScheduledTask).filter_by(parent_id=self.id, status='pending')
        return query.count() >= 1

    def reschedule(self, session, occurrence):
        if self.status != 'active':
            return

        query = session.query(ScheduledTask).filter_by(status='pending', parent_id=self.id)
        if query.count() > 0:
            return

        occurrence = self.schedule.next(occurrence)
        task = ScheduledTask(tag=self.tag, status='pending', description=self.description,
            occurrence=occurrence, retry_backoff=self.retry_backoff,
            retry_limit=self.retry_limit, retry_timeout=self.retry_timeout,
            action_id=self.action_id, failed_action_id=self.failed_action_id,
            completed_action_id=self.completed_action_id, parent_id=self.id)

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
                self.failed_action = Action.polymorphic_create(failed_action)
        if completed_action:
            if self.completed_action:
                self.completed_action.update_with_mapping(completed_action)
            else:
                self.completed_action = Action.polymorphic_create(completed_action)

        session.flush()
        if self.status == 'active' and not self.has_pending_task(session):
            self.reschedule(session, datetime.now(UTC))

class Execution(Model):
    """A task execution."""

    class meta:
        schema = schema
        tablename = 'execution'
        constraints = [UniqueConstraint('task_id', 'attempt')]

    id = Identifier()
    task_id = ForeignKey('scheduled_task.task_id', nullable=False, ondelete='CASCADE')
    attempt = Integer(nullable=False)
    status = Enumeration('completed failed')
    started = DateTime(timezone=True)
    completed = DateTime(timezone=True)
    result = Text()

def create_test_task(session, tag, delay=0, status='complete', result=None,
    retry_limit=2, retry_timeout=300):

    task = Task(tag=tag, occurrence=datetime.utcnow() + timedelta(seconds=delay),
        retry_limit=retry_limit, retry_timeout=retry_timeout)
    task.action = TestAction(status=status, result=result)

    session.add(task)
    session.commit()
