from spire.core import Dependency
from spire.mesh import ModelController
from spire.schema import SchemaDependency

from platoon import resources
from platoon.controllers.task import TaskController
from platoon.idler import Idler
from platoon.models import *

class ScheduledTaskController(TaskController, ModelController):
    resource = resources.ScheduledTask
    version = (1, 0)

    model = ScheduledTask
    mapping = 'id tag description status occurrence retry_backoff retry_limit retry_timeout created'

    idler = Dependency(Idler)
    schema = SchemaDependency('platoon')

    def _annotate_resource(self, request, model, resource, data):
        TaskController._annotate_resource(self, request, model, resource, data)
        if data and 'include' in data and 'executions' in data['include']:
            resource['executions'] = [execution.extract_dict(exclude='id task_id')
                for execution in model.executions]
