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
    status = Enumeration('pending initiating executing completed failed aborted',
        nullable=False, default='pending')
    input = Json()
    output = Json()
    progress = Json()
    started = DateTime(timezone=True)
    ended = DateTime(timezone=True)

    executor_endpoint = relationship('ExecutorEndpoint',
        backref=backref('processes', lazy='dynamic'))
    queue = relationship(Queue, backref=backref('processes', lazy='dynamic'))

    @property
    def endpoint(self):
        return self.executor_endpoint.endpoint

    @property
    def executor(self):
        return self.executor_endpoint.executor
    
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

    def execute(self, session):
        pass

    def initiate(self, session):
        self.started = current_timestamp()
        data = {'id': self.id, 'tag': self.tag, 'input': self.input}

        try:
            response = InitiationResponse.process(self.endpoint.request(data))
        except Exception, exception:
            log('exception', 'initiation of %s failed', repr(self))
            return self._fail_process()

        self.status = response['status']
        if self.status == 'completed':
            self._complete_process(response.get('output'))

    @classmethod
    def process_processes(cls, schema, threads):
        session = schema.session
        cls._process_pending_processes(schema, session, threads)

    def _complete_process(self, output=None):
        self.status = 'completed'
        self.completed = current_timestamp()
        self.output = output

        data = {'id': self.id, 'tag': self.tag, 'status': self.status, 'output': self.output}
        try:
            self.queue.endpoint.request(data)
        except Exception, exception:
            self.status = 'failed'
            log('exception', 'queue notification on completion failed for %s', repr(self))

    def _fail_process(self):
        self.status = 'failed'

        data = {'id': self.id, 'tag': self.tag, 'status': self.status}
        try:
            self.queue.endpoint.request(data)
        except Exception, exception:
            log('exception', 'queue notification on failure failed for %s', repr(self))

    @classmethod
    def _process_pending_processes(cls, schema, session, threads):
        processes = list(session.query(cls).with_lockmode('update').filter_by(status='pending'))
        if not processes:
            return

        for process in processes:
            process.status = 'initiating'
        
        session.commit()
        for process in processes:
            log('info', 'initiating %s', repr(process))
            threads.enqueue(ThreadPackage(schema.get_session(True), process, 'initiate'))
