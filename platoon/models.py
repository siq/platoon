from datetime import datetime, timedelta
from httplib import HTTPConnection
from traceback import format_exc
from urlparse import urlparse

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
        else:
            return (self.status == 'complete'), self.result

class HttpRequestAction(Action):
    """An http request action."""

    class meta:
        polymorphic_identity = 'http-request'
        schema = schema
        tablename = 'http_request_action'

    action_id = ForeignKey('action.id', nullable=False, primary_key=True)
    url = Text(nullable=False)
    method = Enumeration('DELETE GET HEAD OPTIONS POST PUT', nullable=False)
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

class Task(Model):
    """A queue task."""

    class meta:
        schema = schema
        tablename = 'task'

    id = Identifier()
    tag = Text(nullable=False)
    description = Text()
    status = Enumeration('pending completed aborted retrying failed',
        nullable=False, default='pending')
    occurrence = DateTime(nullable=False)
    retry_backoff = Float()
    retry_limit = Integer(nullable=False, default=2)
    retry_timeout = Integer(nullable=False, default=300)
    action_id = ForeignKey('action.id', nullable=False)
    failed_action_id = ForeignKey('action.id')
    completed_action_id = ForeignKey('action.id')

    action = relationship('Action', primaryjoin='Action.id==Task.action_id')
    failed_action = relationship('Action', primaryjoin='Action.id==Task.failed_action_id')
    completed_action = relationship('Action', primaryjoin='Action.id==Task.completed_action_id')
    executions = relationship('Execution', backref='task', order_by='Execution.attempt')

    def __repr__(self):
        return 'Task(%s, %s)' % (self.id, self.tag)

    @classmethod
    def create(cls, session, tag, action, occurrence=None, failed_action=None,
            completed_action=None, description=None, retry_limit=2, retry_timeout=300):

        occurrence = occurrence or datetime.utcnow()
        task = Task(tag=tag, description=description, occurrence=occurrence,
            retry_limit=retry_limit, retry_timeout=retry_timeout)

        task.action = Action.polymorphic_create(action)
        if failed_action:
            task.failed_action = Action.polymorphic_create(failed_action)
        if completed_action:
            task.completed_action = Action.polymorphic_create(completed_action)

        session.add(task)
        return task

    def execute(self, session):
        execution = Execution(task_id=self.id, attempt=len(self.executions) + 1)
        session.add(execution)

        execution.started = datetime.utcnow()
        try:
            status, execution.result = self.action.execute()
        except Exception, exception:
            status = FAILED
            execution.result = format_exc()

        execution.completed = datetime.utcnow()
        if status == COMPLETED:
            self.status = execution.status = 'completed'
            log('info', '%s completed (attempt %d)', repr(self), execution.attempt)
            if self.completed_action_id:
                session.add(Task(tag='%s-completed' % self.tag, occurrence=datetime.utcnow(),
                    action_id=self.completed_action_id))
        elif execution.attempt == (self.retry_limit + 1):
            self.status = 'failed'
            log('error', '%s failed (attempt %d), aborting', repr(self), execution.attempt)
            if self.failed_action_id:
                session.add(Task(tag='%s-failed' % self.tag, occurrence=datetime.utcnow(),
                    action_id=self.failed_action_id))
        else:
            self.status = 'retrying'
            self.occurrence = self._calculate_retry(execution)
            if status == FAILED:
                log('warning', '%s failed (attempt %d), retrying', repr(self), execution.attempt)
            else:
                log('info', '%s not yet complete (attempt %s), retrying',
                    repr(self), execution.attempt)

    def _calculate_retry(self, execution):
        timeout = self.retry_timeout
        if self.retry_backoff is not None:
            timeout *= (self.retry_backoff * execution.attempt)
        return datetime.utcnow() + timedelta(seconds=timeout)

class Execution(Model):
    """A task execution."""

    class meta:
        schema = schema
        tablename = 'execution'
        constraints = [UniqueConstraint('task_id', 'attempt')]

    id = Identifier()
    task_id = ForeignKey('task.id', nullable=False)
    attempt = Integer(nullable=False)
    status = Enumeration('completed failed')
    started = DateTime()
    completed = DateTime()
    result = Text()

def create_test_task(session, tag, delay=0, status='complete', result=None,
    retry_limit=2, retry_timeout=300):

    task = Task(tag=tag, occurrence=datetime.utcnow() + timedelta(seconds=delay),
        retry_limit=retry_limit, retry_timeout=retry_timeout)
    task.action = TestAction(status=status, result=result)

    session.add(task)
    session.commit()
