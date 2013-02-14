from spire.mesh import ModelController
from spire.schema import SchemaDependency

from platoon import resources
from platoon.models import *

class ProcessController(ModelController):
    resource = resources.Process
    version = (1, 0)

    mapping = 'id queue_id tag timeout status input output progress state started ended'
    model = Process
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
