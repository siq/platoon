from mesh.standard import *
from scheme import *

class Schedule(Resource):
    """A task schedule."""

    name = 'schedule'
    version = 1
    requests = 'create delete get put query update'

    class schema:
        id = UUID(operators='equal')
        name = Text()
        schedule = Enumeration('fixed', nonempty=True)
        anchor = DateTime(nonempty=True, utc=True)
        interval = Integer(nonempty=True)

TaskStructure = Structure(
    structure={
        'http-request': {
            'url': Text(nonempty=True),
            'method': Text(nonempty=True),
            'mimetype': Text(),
            'data': Text(),
            'headers': Map(Text(nonempty=True), nonnull=True),
            'timeout': Integer(nonnull=True, default=30),
        },
        'test': {
            'status': Enumeration('complete fail exception', nonempty=True),
            'result': Text(),
        }
    },
    polymorphic_on=Enumeration('http-request test', name='type', nonempty=True),
    nonnull=True)

class Task(Resource):
    """A queue task."""

    class schema:
        id = UUID(operators='equal')
        tag = Text(nonempty=True, operators='equal')
        description = Text()
        retry_backoff = Float()
        retry_limit = Integer(nonnull=True, default=2)
        retry_timeout = Integer(nonnull=True, default=300)
        task = TaskStructure.clone(required=True)
        completed = TaskStructure
        failed = TaskStructure

class ScheduledTask(Task):
    """A scheduled task."""

    name = 'scheduledtask'
    version = 1

    class schema:
        status = Enumeration('pending executing retrying aborted completed failed',
            nonnull=True, oncreate=False)
        occurrence = DateTime(nonnull=True, utc=True)
        executions = Sequence(Structure({
            'attempt': Integer(),
            'status': Enumeration('completed failed'),
            'started': DateTime(utc=True),
            'completed': DateTime(utc=True),
            'result': Text(),
        }), nonnull=True, deferred=True, readonly=True)

class RecurringTask(Task):
    """A recurring task."""

    name = 'recurringtask'
    version = 1
    requests = 'create delete get put query update'

    class schema:
        status = Enumeration('active inactive', nonnull=True, default='active')
        schedule_id = UUID(nonempty=True)
