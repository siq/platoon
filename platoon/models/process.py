from traceback import format_exc

from mesh.exceptions import *
from scheme import current_timestamp
from spire.schema import *
from spire.support.logs import LogHelper

from platoon.constants import *
from platoon.queue import ThreadPackage
from platoon.models.queue import Queue
from platoon.resources.process import InitiationResponse

log = LogHelper('platoon')
schema = Schema('platoon')

class Request(Model):
    """A process request."""

    class meta:
        schema = schema
        tablename = 'request'

    id = Identifier()
    process_id = ForeignKey('process.id', nullable=False, ondelete='CASCADE')
    occurrence = DateTime(timezone=True, nullable=False, default=current_timestamp)
    type = Enumeration('executor-aborted queue-completed', nullable=False)
    status = Enumeration('completed failed', nullable=False)

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
    requests = relationship(Request, backref='process',
        cascade='all,delete-orphan', passive_deletes=True)

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

        payload = self._construct_payload(status='completed', output=self.output)
        try:
            self.queue.endpoint.request(data)
        except Exception, exception:
            log('exception', 'queue notification on completion failed for %s', repr(self))
            self.status = 'completing'

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
            return self._fail_process()

        self.status = response['status']
        if self.status == 'completed':
            self.complete(session, response.get('output'), True)

    @classmethod
    def process_processes(cls, session, taskqueue):
        pass

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

    def _fail_process(self):
        self.status = 'failed'

        data = {'id': self.id, 'tag': self.tag, 'status': self.status}
        try:
            self.queue.endpoint.request(data)
        except Exception, exception:
            log('exception', 'queue notification on failure failed for %s', repr(self))

