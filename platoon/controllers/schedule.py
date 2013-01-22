from spire.mesh import ModelController
from spire.schema import SchemaDependency

from platoon import resources
from platoon.models import *

class ScheduleController(ModelController):
    resource = resources.Schedule
    version = (1, 0)

    model = Schedule
    mapping = 'id name schedule anchor interval'
    schema = SchemaDependency('platoon')
