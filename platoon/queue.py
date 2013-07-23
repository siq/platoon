from datetime import datetime, time

from scheme import current_timestamp
from spire.core import Component, Dependency
from spire.support.daemon import Daemon
from spire.support.logs import LogHelper
from spire.schema import SchemaDependency
from spire.support.threadpool import ThreadPool

from platoon.idler import Idler

log = LogHelper('platoon')

class ThreadPackage(object):
    def __init__(self, session, model, method, **params):
        self.method = method
        self.model = model
        self.params = params
        self.session = session

    def __call__(self):
        session = self.session
        model = session.merge(self.model, load=False)

        method = getattr(model, self.method)
        try:
            method(session, **self.params)
        except Exception:
            session.rollback()
            log('exception', '%s raised uncaught exception', repr(model))
        else:
            session.commit()

class TaskQueue(Component, Daemon):
    """An asynchronous task queue."""

    idler = Dependency(Idler)
    schema = SchemaDependency('platoon')
    threads = Dependency(ThreadPool)

    def enqueue(self, model, method, **params):
        session = self.schema.get_session(True)
        self.threads.enqueue(ThreadPackage(session, model, method, **params))

    def run(self):
        from platoon.models import Event, Process, ScheduledTask

        idler = self.idler
        schema = self.schema
        session = schema.session
        threads = self.threads

        ScheduledTask.retry_executing_tasks(session)
        try:
            while True:
                idler.idle()
                try:
                    Event.process_events(session)
                    Process.process_processes(self, session)
                    ScheduledTask.process_tasks(self, session)
                finally:
                    session.close()
        except Exception:
            log('exception', 'exception raised by task queue')
