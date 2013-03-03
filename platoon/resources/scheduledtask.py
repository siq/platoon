from mesh.standard import *
from scheme import *

from platoon.resources.task import Task

__all__ = ('ScheduledTask',)

class ScheduledTask(Task):
    """A scheduled task."""

    name = 'scheduledtask'
    version = 1

    class schema:
        status = Enumeration('pending executing retrying aborted completed failed',
            nonnull=True, oncreate=False)
        occurrence = DateTime(nonnull=True, utc=True)
        executions = Sequence(Structure({
            'attempt': Integer(),
            'status': Enumeration('completed failed'),
            'started': DateTime(utc=True),
            'completed': DateTime(utc=True),
            'result': Text(),
        }), nonnull=True, deferred=True, readonly=True)

    class create(Resource.create):
        fields = {
            'delta': Integer(nonnull=True, minimum=0),
        }

