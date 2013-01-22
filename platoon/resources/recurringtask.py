from mesh.standard import *
from scheme import *

from platoon.resources.task import Task

__all__ = ('RecurringTask',)

class RecurringTask(Task):
    """A recurring task."""

    name = 'recurringtask'
    version = 1
    requests = 'create delete get put query update'

    class schema:
        status = Enumeration('active inactive', nonnull=True, default='active')
        schedule_id = UUID(nonempty=True)
