from httplib import HTTPConnection
from urlparse import urlparse

from scheme import UTC, current_timestamp
from scheme.formats import Json
from spire.core import get_unit
from spire.schema import *
from spire.support.logs import LogHelper

from platoon.constants import *

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
        ScheduledTask.purge(session, platoon.configuration['completed_task_lifetime'])

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
            path = '%s?%s' % (path, body)
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
