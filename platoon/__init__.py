from mesh.standard import Bundle, mount
from scheme import Integer
from spire.core import Component, Configuration
from spire.mesh import MeshServer

import platoon.models
from platoon import resources
from platoon.queue import TaskQueue

API = Bundle('platoon',
    mount(resources.Event, 'platoon.controllers.EventController'),
    mount(resources.Schedule, 'platoon.controllers.ScheduleController'),
    mount(resources.RecurringTask, 'platoon.controllers.RecurringTaskController'),
    mount(resources.ScheduledTask, 'platoon.controllers.ScheduledTaskController'),
    mount(resources.SubscribedTask, 'platoon.controllers.SubscribedTaskController'),
)

class APIServer(MeshServer):
    pass

class Platoon(Component):
    configuration = Configuration({
        'completed_event_lifetime': Integer(nonnull=True, default=30),
        'completed_task_lifetime': Integer(nonnull=True, default=30),
    })

    api = APIServer.deploy(bundles=[API], path='/')
