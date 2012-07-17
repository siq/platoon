from spire.core import Dependency
from spire.mesh import ModelController
from spire.schema import SchemaDependency

from platoon.idler import Idler
from platoon.models import *
from platoon.resources import Task as TaskResource

class TaskController(ModelController):
    resource = TaskResource
    version = (1, 0)

    model = Task
    mapping = 'id tag description status occurrence retry_limit retry_timeout'

    idler = Dependency(Idler)
    schema = SchemaDependency('platoon')

    struct_mapping = (('task', 'action'), ('failed', 'failed_action'),
        ('completed', 'completed_action'))

    def create(self, request, response, subject, data):
        for field, attr in self.struct_mapping:
            value = data.pop(field, None)
            if value:
                data[attr] = value

        session = self.schema.session
        task = Task.create(session, **data)
        session.commit()

        self.idler.interrupt()
        response({'id': task.id})

    def _annotate_resource(self, request, model, resource, data):
        for field, attr in self.struct_mapping:
            resource[field] = getattr(model, attr).extract_dict(exclude='id')

        if data and 'include' in data and 'executions' in data['include']:
            resource['executions'] = [execution.extract_dict(exclude='id task_id')
                for execution in model.executions]
