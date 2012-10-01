from mesh.standard import Bundle, mount

from platoon import resources

API = Bundle('platoon',
    mount(resources.Event, 'platoon.controllers.EventController'),
    mount(resources.Schedule, 'platoon.controllers.ScheduleController'),
    mount(resources.RecurringTask, 'platoon.controllers.RecurringTaskController'),
    mount(resources.ScheduledTask, 'platoon.controllers.ScheduledTaskController'),
    mount(resources.SubscribedTask, 'platoon.controllers.SubscribedTaskController'),
)
