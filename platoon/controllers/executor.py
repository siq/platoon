from spire.mesh import ModelController
from spire.schema import SchemaDependency

from platoon import resources
from platoon.models import *

class ExecutorController(ModelController):
    resource = resources.Executor
    version = (1, 0)

    mapping = 'id name status'
    model = Executor
    schema = SchemaDependency('platoon')

    def create(self, request, response, subject, data):
        session = self.schema.session
        subject = self.model.create(session, **data)

        session.commit()
        response({'id': subject.id})

    def update(self, request, response, subject, data):
        if not data:
            return response({'id': subject.id})

        session = self.schema.session
        subject.update(session, **data)

        session.commit()
        response({'id': subject.id})

    def _annotate_resource(self, request, model, resource, data):
        endpoints = model.endpoints
        if endpoints:
            resource['endpoints'] = {}
            for subject, endpoint in endpoints.iteritems():
                resource['endpoints'][subject] = endpoint.extract_dict(exclude='id endpoint_id')
