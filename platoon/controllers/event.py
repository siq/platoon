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
