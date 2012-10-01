from scheme import Integer
from spire.core import Component, Configuration
from spire.mesh import MeshServer

import platoon.models
from platoon.bundles import API
from platoon.queue import TaskQueue

class APIServer(MeshServer):
    pass

class Platoon(Component):
    configuration = Configuration({
        'completed_event_lifetime': Integer(nonnull=True, default=30),
        'completed_task_lifetime': Integer(nonnull=True, default=30),
    })

    api = APIServer.deploy(bundles=[API], path='/')
