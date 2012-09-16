from spire.core import Dependency
from spire.mesh import ModelController
from spire.schema import SchemaDependency

from platoon import resources
from platoon.idler import Idler
from platoon.models import *

class EventController(ModelController):
    resource = resources.Event
    version = (1, 0)

    model = Event
    mapping = 'id topic aspects'

    idler = Dependency(Idler)
    schema = SchemaDependency('platoon')

    def create(self, request, response, subject, data):
        subject = self.model.create(self.schema.session, **data)
        self.schema.session.commit()

        self.idler.interrupt()
        response({'id': subject.id})

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
        self._transpose_struct_fields(data)
        session = self.schema.session

        subject = self.model.create(session, **data)
        session.commit()

        self.idler.interrupt()
        response({'id': subject.id})

    def update(self, request, response, subject, data):
        if not data:
            return response({'id': subject.id})

        self._transpose_struct_fields(data)
        session = self.schema.session

        subject.update(session, **data)
        session.commit()

        self.idler.interrupt()
        response({'id': subject.id})

    def _annotate_resource(self, request, model, resource, data):
        for field, attr in self.struct_mapping:
            value = getattr(model, attr)
            if value:
                resource[field] = value.extract_dict(exclude='id action_id')

    def _transpose_struct_fields(self, data):
        for field, attr in self.struct_mapping:
            value = data.pop(field, None)
            if value:
                data[attr] = value

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

class SubscribedTaskController(TaskController, ModelController):
    resource = resources.SubscribedTask
    version = (1, 0)

    model = SubscribedTask
    mapping = 'id tag description topic aspects activation_limit retry_backoff retry_limit retry_timeout'

    idler = Dependency(Idler)
    schema = SchemaDependency('platoon')
