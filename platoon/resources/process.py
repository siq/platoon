from mesh.standard import *
from scheme import *

from platoon.resources.executor import Endpoint

class Process(Resource):
    """A process."""

    name = 'process'
    version = 1

    class schema:
        id = UUID(nonempty=True, operators='equal')
        queue_id = Token(nonempty=True, operators='equal')
        tag = Text(nonempty=True, operators='equal')
        timeout = Integer()
        status = Enumeration('pending initiating executing completed failed aborted',
            oncreate=False, operators='equal in')
        input = Field()
        output = Field()
        progress = Field()
        started = DateTime(utc=True, readonly=True)
        ended = DateTime(utc=True, readonly=True)

    class update(Resource.update):
        schema = {
            'status': Enumeration('completed aborted'),
            'output': Field(),
            'progress': Field(),
        }

InitiationResponse = Structure({
    'status': Enumeration('executing completed failed', nonempty=True),
    'progress': Field(),
    'output': Field(),
}, nonnull=True)
