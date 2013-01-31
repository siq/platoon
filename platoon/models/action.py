from scheme import UTC, current_timestamp
from scheme import formats
from spire.core import get_unit
from spire.schema import *
from spire.support.logs import LogHelper

from platoon.constants import *
from platoon.support.http import http_request

__all__ = ('HttpRequestAction', 'InternalAction', 'TaskAction', 'TestAction')

log = LogHelper('platoon')
schema = Schema('platoon')

class TaskAction(Model):
    """A task action."""

    class meta:
        polymorphic_on = 'type'
        schema = schema
        tablename = 'action'

    id = Identifier()
    type = Enumeration('http-request internal process test', nullable=False)

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
        from platoon.models import Event, ScheduledTask, SubscribedTask
        platoon = get_unit('platoon.component.Platoon')

        Event.purge(session, platoon.configuration['completed_event_lifetime'])
        ScheduledTask.purge(session, platoon.configuration['completed_task_lifetime'])
        SubscribedTask.purge(session, platoon.configuration['completed_task_lifetime'])

        session.commit()

class ProcessAction(TaskAction):
    """A process action."""

    class meta:
        polymorphic_identity = 'process'
        schema = schema
        tablename = 'process_action'

    action_id = ForeignKey('action.id', nullable=False, primary_key=True, ondelete='CASCADE')
    process_id = ForeignKey('process.id', nullable=False)
    action = Enumeration(PROCESS_TASK_ACTIONS, nullable=False)

    process = relationship('Process')

    def execute(self, task, session):
        method = self.action.replace('-', '_')
        getattr(self.process, method)(session)

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
        body = self._prepare_body(task, self.data)
        response = http_request(self.method, self.url, body,
            self.mimetype, self.headers, self.timeout)

        if response.status == PARTIAL:
            status = RETRY
        elif 200 <= response.status <= 299:
            status = COMPLETED
        else:
            status = FAILED

        return status, response.dump()

    def _prepare_body(self, task, body):
        if self.mimetype != 'application/json':
            return body

        injections, params = self.injections, task.parameters
        if not (injections and params):
            return body

        body = (formats.Json.unserialize(body) if body else {})
        for key in injections:
            if key in params:
                body[key] = params[key]

        return formats.Json.serialize(body)
