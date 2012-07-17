from mesh.standard import *
from scheme import *

TaskStructure = Structure(
    structure={
        'http-request': {
            'url': Text(nonempty=True),
            'method': Enumeration('DELETE GET HEAD OPTIONS POST PUT', nonempty=True),
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

    name = 'task'
    version = 1

    class schema:
        id = UUID(operators='equal')
        tag = Text(nonempty=True, operators='equal')
        description = Text()
        status = Enumeration('pending completed aborted retrying failed', oncreate=False)
        occurrence = DateTime(nonnull=True, timezone=UTC)
        retry_backoff = Float(nonnull=True)
        retry_limit = Integer(nonnull=True, default=2)
        retry_timeout = Integer(nonnull=True, default=300)
        task = TaskStructure.clone(required=True)
        completed = TaskStructure
        failed = TaskStructure
        executions = Sequence(Structure({
            'attempt': Integer(),
            'status': Enumeration('completed failed'),
            'started': DateTime(timezone=UTC),
            'completed': DateTime(timezone=UTC),
            'result': Text(),
        }), nonnull=True, deferred=True, readonly=True)
