from mesh.standard import *
from scheme import *

from platoon.support.scheduling import validate_range, validate_weekday

__all__ = ('Schedule',)

class Schedule(Resource):
    """A task schedule."""

    name = 'schedule'
    version = 1
    requests = 'create delete get put query update'

    class schema:
        id = UUID(operators='equal')
        name = Text()
        description = Text(readonly=True)
        next = DateTime(readonly=True)
        schedule = Structure(
            structure={
                'fixed': {
                    'anchor': DateTime(utc=True, nonempty=True),
                    'interval': Integer(nonempty=True),
                },
                'logical': {
                    'anchor': DateTime(utc=True),
                    'month': Text(),
                    'day': Text(),
                    'weekday': Text(),
                    'hour': Text(),
                    'minute': Text(),
                },
                'monthly': {
                    'anchor': DateTime(utc=True, nonempty=True),
                    'strategy': Enumeration('day weekday', nonempty=True, default='day'),
                    'interval': Integer(nonempty=True, minimum=1),
                },
                'weekly': {
                    'anchor': DateTime(utc=True, nonempty=True),
                    'interval': Integer(nonempty=True, minimum=1),
                    'sunday': Boolean(),
                    'monday': Boolean(),
                    'tuesday': Boolean(),
                    'wednesday': Boolean(),
                    'thursday': Boolean(),
                    'friday': Boolean(),
                    'saturday': Boolean(),
                },
            },
            polymorphic_on='type',
            nonempty=True)

    class create(Resource.create):
        support_returning = True

    class update(Resource.update):
        support_returning = True
