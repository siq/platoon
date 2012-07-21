from datetime import datetime

from spire.core import Component, Dependency
from spire.schema import SchemaDependency
from spire.support.daemon import Daemon
from spire.support.logs import LogHelper
from spire.support.threadpool import ThreadPool

from platoon.idler import Idler
from platoon.models import *

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
        pending = session.query(Task).filter(Task.status.in_(('pending', 'retrying')))

        while True:
            idler.idle()
            try:
                query = pending.filter(Task.occurrence <= datetime.utcnow())
                tasks = list(query)

                query.update({'status': 'executing'}, False)
                session.commit()

                for task in tasks:
                    log('info', 'processing %s', repr(task))
                    package = TaskPackage(task, schema.get_session(True))
                    threads.enqueue(package)
            finally:
                session.close()
