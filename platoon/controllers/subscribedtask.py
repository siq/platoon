from spire.core import Dependency
from spire.mesh import ModelController
from spire.schema import SchemaDependency

from platoon import resources
from platoon.controllers.task import TaskController
from platoon.idler import Idler
from platoon.models import *

class SubscribedTaskController(TaskController, ModelController):
    resource = resources.SubscribedTask
    version = (1, 0)

    model = SubscribedTask
    mapping = 'id tag description topic aspects activation_limit retry_backoff retry_limit retry_timeout'

    idler = Dependency(Idler)
    schema = SchemaDependency('platoon')
