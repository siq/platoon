from datetime import datetime

from scheme import Integer, UTC
from spire.core import Component, Configuration
from spire.mesh import MeshServer
from spire.schema import Schema

from platoon import models
from platoon.bundles import API
from platoon.queue import TaskQueue

schema = Schema('platoon')

class APIServer(MeshServer):
    pass

class Platoon(Component):
    configuration = Configuration({
        'completed_event_lifetime': Integer(nonnull=True, default=30),
        'completed_task_lifetime': Integer(nonnull=True, default=30),
    })

    api = APIServer.deploy(bundles=[API], path='/')

@schema.constructor()
def bootstrap_purge_task(session):
    schedule = models.FixedSchedule(
        id='00000000-0000-0000-0000-000000000001',
        name='Purge Schedule',
        anchor=datetime(2000, 1, 1, 2, 0, 0, tzinfo=UTC),
        interval=86400)
    action = models.InternalAction(
        id='00000000-0000-0000-0000-000000000001',
        purpose='purge')
    task = models.RecurringTask(
        id='00000000-0000-0000-0000-000000000001',
        tag='purge-database',
        schedule=schedule,
        schedule_id=schedule.id,
        action_id=action.id,
        retry_limit=0)

    session.merge(schedule)
    session.merge(action)
    session.merge(task)
    session.flush()
    task.reschedule(session)
    session.commit()

