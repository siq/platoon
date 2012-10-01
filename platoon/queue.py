from datetime import datetime, time

from scheme import current_timestamp
from spire.core import Component, Dependency
from spire.support.daemon import Daemon
from spire.support.logs import LogHelper
from spire.schema import SchemaDependency
from spire.support.threadpool import ThreadPool

from platoon.idler import Idler
from platoon.models import Event, InternalAction, RecurringTask, ScheduledTask, Schedule

log = LogHelper('platoon')

class TaskPackage(object):
    def __init__(self, task, session):
        self.session = session
        self.task = task

    def __repr__(self):
        return repr(self.task)

    def __call__(self):
        session = self.session
        task = session.merge(self.task)

        try:
            task.execute(session)
        except Exception:
            session.rollback()
            log('exception', '%s raised uncaught exception', repr(task))
        else:
            session.commit()

class TaskQueue(Component, Daemon):
    """An asynchronous task queue."""

    idler = Dependency(Idler)
    schema = SchemaDependency('platoon')
    threads = Dependency(ThreadPool)

    def run(self):
        idler = self.idler
        schema = self.schema
        threads = self.threads

        session = schema.session
        pending_events = session.query(Event).with_lockmode('update').filter_by(status='pending')
        pending_tasks = session.query(ScheduledTask).with_lockmode('update').filter(
            ScheduledTask.status.in_(('pending', 'retrying')))

        while True:
            idler.idle()
            try:
                for event in pending_events:
                    event.schedule_tasks(session)
                else:
                    session.commit()

                occurrence = current_timestamp()
                tasks = list(pending_tasks.filter(ScheduledTask.occurrence <= occurrence))

                if not tasks:
                    continue
                for task in tasks:
                    task.status = 'executing'

                session.commit()
                for task in tasks:
                    log('info', 'processing %s', repr(task))
                    package = TaskPackage(task, schema.get_session(True))
                    threads.enqueue(package)
            finally:
                session.close()
