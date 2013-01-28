from mesh.standard import *
from scheme import *

from platoon.resources.executor import Endpoint

__all__ = ('Queue',)

class Queue(Resource):
    """A task queue."""

    name = 'queue'
    version = 1
    requests = 'create delete get put query update'

    class schema:
        id = Token(nonempty=True, oncreate=True, operators='equal')
        subject = Token(nonempty=True, operators='equal')
        name = Text(operators='equal')
        status = Enumeration('active inactive', nonnull=True, default='active')
        endpoint = Endpoint
