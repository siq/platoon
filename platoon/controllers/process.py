from spire.core import Dependency
from spire.mesh import ModelController
from spire.schema import SchemaDependency

from platoon import resources
from platoon.models import *
from platoon.queue import TaskQueue

class ProcessController(ModelController):
    resource = resources.Process
    version = (1, 0)

    mapping = 'id queue_id tag timeout input output progress started ended'
    model = Process

    taskqueue = Dependency(TaskQueue)
    schema = SchemaDependency('platoon')

    def create(self, request, response, subject, data):
        session = self.schema.session
        subject = self.model.create(session, **data)
        
        session.commit()
        self.taskqueue.enqueue(subject, 'initiate')
        response({'id': subject.id})

    def update(self, request, response, subject, data):
        if not data:
            return response({'id': subject.id})

        session = self.schema.session
        task = subject.update(session, **data)

        session.commit()
        if task:
            self.taskqueue.enqueue(subject, task)

        response({'id': subject.id})

    def _annotate_resource(self, request, model, resource, data):
        resource['status'] = model.public_status
