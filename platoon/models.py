from datetime import datetime, timedelta
from httplib import HTTPConnection
from traceback import format_exc
from urlparse import urlparse

from scheme import UTC, current_timestamp
from scheme.formats import Json
from spire.core import get_unit
from spire.schema import *
from spire.support.logs import LogHelper
from sqlalchemy.sql import bindparam, text

COMPLETED = 'completed'
FAILED = 'failed'
RETRY = 'retry'

PARTIAL = 206

log = LogHelper('platoon')
schema = Schema('platoon')

class TaskAction(Model):
    """A task action."""

    class meta:
        polymorphic_on = 'type'
        schema = schema
        tablename = 'action'

    id = Identifier()
    type = Enumeration('http-request internal test', nullable=False)

class TestAction(TaskAction):
    """A test action."""

    class meta:
        polymorphic_identity = 'test'
        schema = schema
        tablename = 'test_action'

    action_id = ForeignKey('action.id', nullable=False, primary_key=True)
    status = Enumeration('complete fail exception', nullable=False)
    result = Text()

    def execute(self, task, session):
        if self.status == 'exception':
            raise Exception('test exception')
        elif self.status == 'complete':
            return COMPLETED, self.result
        else:
            return FAILED, self.result

class InternalAction(TaskAction):
    """An internal task."""

    class meta:
        polymorphic_identity = 'internal'
        schema = schema
        tablename = 'internal_action'

    action_id = ForeignKey('action.id', nullable=False, primary_key=True, ondelete='CASCADE')
    purpose = Enumeration('purge', nullable=False, unique=True)

    def execute(self, task, session):
        if self.purpose == 'purge':
            self._purge_database(session)

        return COMPLETED, None

    def _purge_database(self, session):
        platoon = get_unit('platoon.Platoon')
        Event.purge(session, platoon.configuration['completed_event_lifetime'])

class HttpRequestAction(TaskAction):
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
    injections = Serialized()

    def execute(self, task, session):
        scheme, host, path = urlparse(self.url)[:3]
        connection = HTTPConnection(host=host, timeout=self.timeout)

        body = self._prepare_body(task, self.data)
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

    def _prepare_body(self, task, body):
        if self.mimetype != 'application/json':
            return body

        injections, params = self.injections, task.parameters
        if not (injections and params):
            return body

        body = (Json.unserialize(body) if body else {})
        for key in injections:
            if key in params:
                body[key] = params[key]

        return Json.serialize(body)

class TaskExecution(Model):
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

    action = relationship(TaskAction, primaryjoin='TaskAction.id==Task.action_id',
        cascade='all')
    failed_action = relationship(TaskAction, primaryjoin='TaskAction.id==Task.failed_action_id',
        cascade='all')
    completed_action = relationship(TaskAction, primaryjoin='TaskAction.id==Task.completed_action_id',
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
    parameters = Serialized()

    parent = relationship('RecurringTask', primaryjoin='RecurringTask.task_id==ScheduledTask.parent_id',
        cascade='all')
    executions = relationship(TaskExecution, backref='task', order_by='TaskExecution.attempt',
        cascade='all,delete-orphan', passive_deletes=True)

    @classmethod
    def create(cls, session, tag, action, status='pending', occurrence=None,
            failed_action=None, completed_action=None, description=None,
            retry_backoff=None, retry_limit=2, retry_timeout=300):

        occurrence = occurrence or datetime.now(UTC)
        task = ScheduledTask(tag=tag, status=status, description=description,
            occurrence=occurrence, retry_backoff=retry_backoff,
            retry_limit=retry_limit, retry_timeout=retry_timeout)

        task.action = TaskAction.polymorphic_create(action)
        if failed_action:
            task.failed_action = TaskAction.polymorphic_create(failed_action)
        if completed_action:
            task.completed_action = TaskAction.polymorphic_create(completed_action)

        session.add(task)
        return task

    def execute(self, session):
        parent = None
        if self.parent_id:
            parent = RecurringTask.load(session, id=self.parent_id, lockmode='update')

        execution = TaskExecution(task_id=self.id, attempt=len(self.executions) + 1)
        session.add(execution)

        execution.started = datetime.now(UTC)
        try:
            status, execution.result = self.action.execute(self, session)
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

    @classmethod
    def spawn(cls, template, occurrence=None, **params):
        occurrence = occurrence or datetime.now(UTC)
        return cls(tag=template.tag, status='pending', description=template.description,
            occurrence=occurrence, retry_backoff=template.retry_backoff,
            retry_limit=template.retry_limit, retry_timeout=template.retry_timeout,
            action_id=template.action_id, failed_action_id=template.failed_action_id,
            completed_action_id=template.completed_action_id, **params)

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
        query = session.query(ScheduledTask).filter_by(parent_id=self.id, status='pending')
        return query.count() >= 1

    def reschedule(self, session, occurrence=None):
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

class Event(Model):
    """An event."""

    class meta:
        schema = schema
        tablename = 'event'

    id = Identifier()
    topic = Token(nullable=False)
    aspects = Hstore()
    status = Enumeration('pending completed', nullable=False, default='pending')
    occurrence = DateTime(timezone=True)

    HSTORE_FILTER = text(':aspects @> subscribed_task.aspects',
        bindparams=[bindparam('aspects', type_=aspects.type)])

    @classmethod
    def create(cls, session, topic, aspects=None):
        event = Event(topic=topic, aspects=aspects, occurrence=datetime.now(UTC))
        session.add(event)
        return event

    def collate_tasks(self, session):
        model = SubscribedTask
        print self.aspects
        return (session.query(model).with_lockmode('update')
            .filter(model.topic==self.topic)
            .filter((model.activation_limit == None) | (model.activations < model.activation_limit))
            .filter(self.HSTORE_FILTER | (model.aspects == None))
            .params(aspects=(self.aspects or {})))

    def describe(self):
        aspects = (self.aspects.copy() if self.aspects is not None else {})
        aspects['topic'] = self.topic
        return aspects

    @classmethod
    def purge(cls, session, lifetime):
        delta = datetime.now(UTC) - timedelta(days=lifetime)
        session.query(cls).filter(cls.status == 'completed', cls.occurrence < delta).delete()

    def schedule_tasks(self, session):
        description = self.describe()
        for task in self.collate_tasks(session):
            task.activate(session, description)

        self.status = 'completed'

def create_test_task(session, tag, delay=0, status='complete', result=None,
    retry_limit=2, retry_timeout=300):

    task = Task(tag=tag, occurrence=datetime.utcnow() + timedelta(seconds=delay),
        retry_limit=retry_limit, retry_timeout=retry_timeout)
    task.action = TestAction(status=status, result=result)

    session.add(task)
    session.commit()
