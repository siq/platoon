from traceback import format_exc

from mesh.exceptions import *
from scheme import current_timestamp
from spire.schema import *
from spire.support.logs import LogHelper
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm.collections import attribute_mapped_collection

from platoon.constants import *
from platoon.queue import ThreadPackage
from platoon.models import ProcessAction, Queue, ScheduledTask
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
    status = Enumeration('pending executing aborting aborted completing completed'
        ' failed timedout', nullable=False, default='pending')
    input = Json()
    output = Json()
    progress = Json()
    started = DateTime(timezone=True)
    ended = DateTime(timezone=True)

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

    @property
    def public_status(self):
        status = self.status
        if status in ('pending', 'initiated'):
            return 'pending'
        elif status in ('executing', 'completing'):
            return 'executing'
        elif status in ('aborting', 'aborted'):
            return 'aborted'
        else:
            return status

    def abort(self, session):
        session.refresh(self, lockmode='update')
        if self.status != 'aborting':
            return

        self.status = 'aborted'
        payload = self._construct_payload(status='aborted')

        try:
            self.endpoint.request(payload)
        except Exception, exception:
            log('exception', 'notification of abortion of %s failed', repr(self))

    def complete(self, session, output=None, bypass_checks=False):
        if not bypass_checks:
            session.refresh(self, lockmode='update')
            if self.status != 'completing':
                return

        self.status = 'completed'
        if not self.completed:
            self.completed = current_timestamp()
        if output:
            self.output = output

        try:
            self._report_completion()
        except Exception:
            self.tasks['report-completion'] = ScheduledTask.create(session,
                tag='report-completion:%s' % self.tag,
                delta=120,
                retry_backoff=1.4, retry_limit=10, retry_timeout=120,
                action=ProcessAction(process=self, action='report-completion'))

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

        self._schedule_immediate_task(session, 'initiate-process')
        return process

    def initiate(self, session):
        session.refresh(self, lockmode='update')
        if self.status != 'pending':
            return

        self.started = current_timestamp()
        payload = self._construct_payload(input=self.input)

        try:
            response = InitiationResponse.process(self.endpoint.request(payload))
        except Exception, exception:
            log('exception', 'initiation of %s failed', repr(self))
            return # need to fail process here

        self.status = response['status']
        if self.status == 'completed':
            self.complete(session, response.get('output'), True)

    def update(self, session, status=None, output=None, progress=None):
        session.refresh(self, lockmode='update')
        if status == 'aborted':
            if self.status in ('pending', 'executing'):
                self.status = 'aborting'
                return 'abort'
        elif status == 'completed':
            if self.status == 'executing':
                self.status = 'completing'
                self.completed = current_timestamp()
                if output:
                    self.output = output
                return 'complete'
        elif progress:
            self.progress = progress
            return 'report'
            
    def _construct_payload(self, **params):
        params.update(id=self.id, tag=self.tag)
        return params

    def _report_abortion(self):
        payload = self._construct_payload(status='aborted')
        self.endpoint.request(payload)

    def _report_completion(self):
        payload = self._construct_payload(status='completed', output=self.output)
        self.queue.endpoint.request(payload)

    def _report_failure(self):
        payload = self._construct_payload(status='failed')
        self.queue.endpoint.request(payload)

    def _report_timeout(self):
        payload = self._construct_payload(status='timedout')
        self.queue.endpoint.request(payload)

    def _schedule_immediate_task(self, session, action):
        self.tasks[action] = ScheduledTask.create(session,
            tag='%s:%s' % (action, self.tag),
            retry_limit=0,
            action=ProcessAction(process_id=self.id, action=action))

class ProcessTask(Model):
    """A process task."""

    class meta:
        constraints = [UniqueConstraint('process_id', 'task_id', 'phase')]
        schema = schema
        tablename = 'process_task'

    id = Identifier()
    process_id = ForeignKey('process.id', nullable=False, ondelete='CASCADE')
    task_id = ForeignKey('scheduled_task.id', nullable=False)
    phase = Enumeration(PROCESS_TASK_ACTIONS, nullable=False)

    process = relationship(Process, backref=backref('process_tasks',
        collection_class=attribute_mapped_collection('phase'),
        cascade='all,delete-orphan', passive_deletes=True))
    task = relationship(ScheduledTask, cascade='all,delete-orphan', single_parent=True)
