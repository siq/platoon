from mesh.standard import *
from scheme import *

__all__ = ('Event',)

class Event(Resource):
    """An event."""

    name = 'event'
    version = 1

    class schema:
        id = UUID()
        topic = Token(nonempty=True)
        aspects = Map(Text())
