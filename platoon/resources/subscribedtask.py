from mesh.standard import *
from scheme import *

from platoon.resources.task import Task

__all__ = ('SubscribedTask',)

class SubscribedTask(Task):
    """A subscribed task."""

    name = 'subscribedtask'
    version = 1

    class schema:
        topic = Token(nonempty=True)
        aspects = Map(Text())
        activation_limit = Integer(minimum=1)
        activated = DateTime(utc=True, readonly=True)
        timeout = Integer()
