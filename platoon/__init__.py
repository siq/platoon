from mesh.standard import Bundle, mount
from spire.core import Component
from spire.mesh import MeshServer

import platoon.models
from platoon import resources
from platoon.queue import TaskQueue

API = Bundle('platoon',
    mount(resources.Schedule, 'platoon.controllers.ScheduleController'),
    mount(resources.RecurringTask, 'platoon.controllers.RecurringTaskController'),
    mount(resources.ScheduledTask, 'platoon.controllers.ScheduledTaskController'),
)

class APIServer(MeshServer):
    pass

class Platoon(Component):
    api = APIServer.deploy(bundles=[API], path='/')
