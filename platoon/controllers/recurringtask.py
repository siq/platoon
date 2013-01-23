from spire.core import Dependency
from spire.mesh import ModelController
from spire.schema import SchemaDependency

from platoon import resources
from platoon.controllers.task import TaskController
from platoon.idler import Idler
from platoon.models import *

class RecurringTaskController(TaskController, ModelController):
    resource = resources.RecurringTask
    version = (1, 0)

    model = RecurringTask
    mapping = 'id tag description status schedule_id retry_backoff retry_limit retry_timeout created'

    idler = Dependency(Idler)
    schema = SchemaDependency('platoon')
