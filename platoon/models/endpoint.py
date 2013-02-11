from spire.schema import *

from platoon.constants import *
from platoon.support.http import http_request

__all__ = ('Endpoint', 'HttpEndpoint')

schema = Schema('platoon')

class Endpoint(Model):
    """An executor endpoint."""

    class meta:
        polymorphic_on = 'type'
        schema = schema
        tablename = 'endpoint'

    id = Identifier()
    type = Enumeration('http', nullable=False)

class HttpEndpoint(Endpoint):
    """An http endpoint."""

    class meta:
        polymorphic_identity = 'http'
        schema = schema
        tablename = 'http_endpoint'

    endpoint_id = ForeignKey('endpoint.id', nullable=False, primary_key=True, ondelete='CASCADE')
    url = Text(nullable=False)
    method = Text(nullable=False, default='POST')
    mimetype = Text(nullable=False, default='application/json')
    headers = Json()
    info = Json()

    def request(self, data, timeout=None):
        if self.info:
            data['info'] = self.info

        response = http_request(self.method, self.url, data, self.mimetype,
            self.headers, timeout, True)

        if response.ok:
            return COMPLETED, response.unserialize()
        else:
            return FAILED, response.dump()
