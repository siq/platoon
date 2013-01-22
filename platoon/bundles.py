from mesh.standard import Bundle, mount

from platoon import resources

API = Bundle('platoon',
    mount(resources.Event, 'platoon.controllers.event.EventController'),
    mount(resources.Schedule, 'platoon.controllers.schedule.ScheduleController'),
    mount(resources.RecurringTask, 'platoon.controllers.recurringtask.RecurringTaskController'),
    mount(resources.ScheduledTask, 'platoon.controllers.scheduledtask.ScheduledTaskController'),
    mount(resources.SubscribedTask, 'platoon.controllers.subscribedtask.SubscribedTaskController'),
)
