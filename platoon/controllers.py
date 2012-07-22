from spire.core import Dependency
from spire.mesh import ModelController
from spire.schema import SchemaDependency

from platoon import resources
from platoon.idler import Idler
from platoon.models import *

class ScheduleController(ModelController):
    resource = resources.Schedule
    version = (1, 0)

    model = Schedule
    mapping = 'id name schedule anchor interval'
    schema = SchemaDependency('platoon')

class TaskController(object):
    struct_mapping = (('task', 'action'), ('failed', 'failed_action'),
        ('completed', 'completed_action'))

    def create(self, request, response, subject, data):
        for field, attr in self.struct_mapping:
            value = data.pop(field, None)
            if value:
                data[attr] = value

        session = self.schema.session
        task = self.model.create(session, **data)
        session.commit()

        self.idler.interrupt()
        response({'id': task.id})

    def _annotate_resource(self, request, model, resource, data):
        for field, attr in self.struct_mapping:
            value = getattr(model, attr)
            if value:
                resource[field] = value.extract_dict(exclude='id action_id')

class RecurringTaskController(TaskController, ModelController):
    resource = resources.RecurringTask
    version = (1, 0)

    model = RecurringTask
    mapping = 'id tag description status schedule_id retry_backoff retry_limit retry_timeout'

    idler = Dependency(Idler)
    schema = SchemaDependency('platoon')

class ScheduledTaskController(TaskController, ModelController):
    resource = resources.ScheduledTask
    version = (1, 0)

    model = ScheduledTask
    mapping = 'id tag description status occurrence retry_backoff retry_limit retry_timeout'

    idler = Dependency(Idler)
    schema = SchemaDependency('platoon')

    def _annotate_resource(self, request, model, resource, data):
        TaskController._annotate_resource(self, request, model, resource, data)
        if data and 'include' in data and 'executions' in data['include']:
            resource['executions'] = [execution.extract_dict(exclude='id task_id')
                for execution in model.executions]
