class TaskSupport(object):
    mixin = 'RecurringTask ScheduledTask'

    @staticmethod
    def prepare_http_task(task):
        task['type'] = 'http-request'
        for key in ('mimetype', 'data', 'headers', 'timeout'):
            if key in task and not task[key]:
                del task[key]
        return task

    @classmethod
    def queue_http_task(cls, tag, task, **params):
        params.update(tag=tag, task=cls.prepare_http_task(task))
        return cls.create(**params)

    def set_http_task(self, task):
        self.task = self.prepare_http_task(task)
        return self
