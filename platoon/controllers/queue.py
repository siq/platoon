from spire.mesh import ModelController
from spire.schema import SchemaDependency

from platoon import resources
from platoon.models import *

class QueueController(ModelController):
    resource = resources.Queue
    version = (1, 0)

    mapping = 'id subject name status'
    model = Queue
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
        endpoint = model.endpoint
        if endpoint:
            resource['endpoint'] = endpoint.extract_dict(exclude='id endpoint_id',
                drop_none=True)
