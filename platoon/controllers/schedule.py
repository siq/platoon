from spire.mesh import ModelController, support_returning
from spire.schema import SchemaDependency

from platoon import resources
from platoon.models import *

class ScheduleController(ModelController):
    resource = resources.Schedule
    version = (1, 0)

    model = Schedule
    mapping = 'id name'
    schema = SchemaDependency('platoon')

    @support_returning
    def create(self, request, response, subject, data):
        session = self.schema.session
        schedule = data.pop('schedule')

        schedule.update(data)
        subject = self.model.create(session, **schedule)

        session.commit()
        return subject

    @support_returning
    def update(self, request, response, subject, data):
        if not data:
            return subject

        session = self.schema.session
        schedule = data.pop('schedule', None) or {}

        schedule.update(data)
        subject.update(session, **schedule)

        session.commit()
        return subject

    def _annotate_resource(self, request, model, resource, data):
        resource['schedule'] = model.extract_dict(exclude='id name schedule_id', drop_none=True)
        resource['description'] = model.describe()
        resource['next'] = model.next()
