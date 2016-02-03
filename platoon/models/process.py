from datetime import timedelta
from traceback import format_exc

from mesh.exceptions import *
from scheme import current_timestamp
from spire.schema import *
from spire.support.logs import LogHelper
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm.collections import attribute_mapped_collection

from platoon.constants import *
from platoon.queue import ThreadPackage
from platoon.models.action import ProcessAction
from platoon.models.queue import Queue
from platoon.models.scheduledtask import ScheduledTask
from platoon.resources.process import InitiationResponse

log = LogHelper('platoon')
schema = Schema('platoon')

class Process(Model):
    """A process."""

    class meta:
        schema = schema
        tablename = 'process'

    id = Identifier()
    queue_id = ForeignKey('queue.id', nullable=False)
    executor_endpoint_id = ForeignKey('executor_endpoint.id')
    tag = Text(nullable=False)
    timeout = Integer()
    status = Enumeration('pending initiating executing aborting aborted completed failed timedout',
        nullable=False, default='pending')
    input = Json()
    output = Json()
    progress = Json()
    state = Json()
    started = DateTime(timezone=True)
    ended = DateTime(timezone=True)
    communicated = DateTime(timezone=True)

    executor_endpoint = relationship('ExecutorEndpoint',
        backref=backref('processes', lazy='dynamic'))
    queue = relationship(Queue, backref=backref('processes', lazy='dynamic'))
    tasks = association_proxy('process_tasks', 'task',
        creator=lambda k, v: ProcessTask(phase=k, task=v))

    @property
    def endpoint(self):
        return self.executor_endpoint.endpoint

    @property
    def executor(self):
        return self.executor_endpoint.executor

    def abandon(self, session):
        session.refresh(self, lockmode='update')
        if self.status != 'executing':
            return

        self.verify(session, True)
        if self.status != 'executing':
            return

        self.status = 'timedout'
        self._schedule_task(session, 'report-timeout-to-executor', limit=10)
        self._schedule_task(session, 'report-timeout-to-queue', limit=10)

    def abort(self, session):
        session.refresh(self, lockmode='update')
        if self.status not in ('pending', 'executing'):
            return

        self.status = 'aborting'
        self._schedule_task(session, 'report-abortion', limit=10)

    def end(self, session, status='completed', output=None, bypass_checks=False):
        if not bypass_checks:
            session.refresh(self, lockmode='update')
            if self.status not in ('aborting', 'executing', 'pending'):
                return

        self.ended = current_timestamp()
        self.status = status
        self.output = output
        self._schedule_task(session, 'report-end', limit=10)

    @classmethod
    def create(cls, session, queue_id, **attrs):
        try:
            queue = Queue.load(session, id=queue_id)
        except NoResultFound:
            raise OperationError(token='invalid-queue-id')

        process = cls(queue_id=queue_id, **attrs)
        session.add(process)

        process.executor_endpoint = queue.assign_executor_endpoint(session)
        if not process.executor_endpoint:
            raise OperationError(token='no-executor-available')

        process._schedule_task(session, 'initiate-process')
        return process

    def initiate_process(self, session):
        session.refresh(self, lockmode='update')
        if self.status != 'pending':
            return

        self.started = current_timestamp()
        payload = self._construct_payload(status='initiating', input=self.input)

        try:
            status, response = self.endpoint.request(payload)
            if status != COMPLETED:
                log('error', 'initiation of %s failed during initial request\n%s', repr(self), response)
                return self.end(session, 'failed', bypass_checks=True)
        except Exception, exception:
            log('exception', 'initiation of %s failed during initial request', repr(self))
            return self.end(session, 'failed', bypass_checks=True)

        try:
            response = InitiationResponse.process(response)
        except Exception, exception:
            log('exception', 'initiation of %s failed due to invalid response', repr(self))
            return self.end(session, 'failed', bypass_checks=True)

        self.status = response['status']
        if self.status in ('completed', 'failed'):
            return self.end(session, self.status, response.get('output'), True)

        state = response.get('state')
        if state:
            self.state = state

    @classmethod
    def process_processes(cls, taskqueue, session):
        occurrence = current_timestamp()
        query = session.query(cls).filter(cls.timeout != None,
            cls.started != None, cls.status == 'executing')

        for process in query:
            if (process.started + timedelta(minutes=process.timeout)) < occurrence:
                log('info', 'abandoning %r due to timing out', process)
                taskqueue.enqueue(process, 'abandon')

    def report_abortion(self, session):
        payload = self._construct_payload(status='aborting', for_executor=True)
        return self.endpoint.request(payload)

    def report_end(self, session):
        payload = self._construct_payload(status=self.status, output=self.output)
        return self.queue.endpoint.request(payload)

    def report_progress(self, session):
        payload = self._construct_payload(status='executing', progress=self.progress)
        return self.queue.endpoint.request(payload)

    def report_timeout_to_executor(self, session):
        payload = self._construct_payload(status='timedout', for_executor=True)
        return self.endpoint.request(payload)

    def report_timeout_to_queue(self, session):
        payload = self._construct_payload(status='timedout')
        return self.queue.endpoint.request(payload)

    def update(self, session, status=None, output=None, progress=None, state=None):
        if status == 'aborting':
            self.abort(session)
        elif status in ('aborted', 'completed', 'failed'):
            self.end(session, status, output)
        elif progress:
            self.progress = progress
            if state:
                self.state = state
            self._schedule_task(session, 'report-progress', limit=3)

    def verify(self, session, bypass_checks=False):
        if not bypass_checks:
            session.refresh(self, lockmode='update')
            if self.status != 'executing':
                return

        payload = self._construct_payload(status='executing', for_executor=True)
        try:
            status, response = self.endpoint.request(payload)
            if status != COMPLETED:
                log('error', 'verification of %s failed during initial request\n%s', repr(self), response)
                return self.end(session, 'failed', bypass_checks=True)
        except Exception:
            log('exception', 'verification of %s failed during initial request', repr(self))
            return self.end(session, 'failed', bypass_checks=True)

        self.communicated = current_timestamp()
        try:
            response = InitiationResponse.process(response)
        except Exception:
            log('exception', 'verification of %s failed due to invalid response', repr(self))
            return self.end(session, 'failed', bypass_checks=True)

        status = response['status']
        if status in ('completed', 'failed'):
            return self.end(session, status, response.get('output'), True)

        state = response.get('state')
        if state:
            self.state = state

    def _construct_payload(self, for_executor=False, **params):
        params.update(id=self.id, tag=self.tag, subject=self.queue.subject)
        if for_executor:
            params['state'] = self.state
        return params

    def _schedule_task(self, session, action, delta=None, limit=0, timeout=120, backoff=1.4):
        self.tasks[action] = ScheduledTask.create(session,
            tag='%s:%s' % (action, self.tag),
            action=ProcessAction(process_id=self.id, action=action),
            delta=delta,
            retry_limit=limit,
            retry_timeout=timeout,
            retry_backoff=backoff)

class ProcessTask(Model):
    """A process task."""

    class meta:
        constraints = [UniqueConstraint('process_id', 'task_id', 'phase')]
        schema = schema
        tablename = 'process_task'

    id = Identifier()
    process_id = ForeignKey('process.id', nullable=False, ondelete='CASCADE')
    task_id = ForeignKey('scheduled_task.task_id', nullable=False, ondelete='CASCADE')
    phase = Enumeration(PROCESS_TASK_ACTIONS, nullable=False)

    process = relationship(Process, backref=backref('process_tasks',
        collection_class=attribute_mapped_collection('phase'),
        cascade='all,delete-orphan', passive_deletes=True))
    task = relationship(ScheduledTask, cascade='all,delete-orphan', single_parent=True)
