from mesh.standard import *
from scheme import *

__all__ = ('Schedule',)

class Schedule(Resource):
    """A task schedule."""

    name = 'schedule'
    version = 1
    requests = 'create delete get put query update'

    class schema:
        id = UUID(operators='equal')
        name = Text()
        schedule = Enumeration('fixed', nonempty=True)
        anchor = DateTime(nonempty=True, utc=True)
        interval = Integer(nonempty=True)
