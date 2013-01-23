from mesh.standard import *
from scheme import *

TaskStructure = Structure(
    structure={
        'http-request': {
            'url': Text(nonempty=True),
            'method': Text(nonempty=True),
            'mimetype': Text(),
            'data': Text(),
            'headers': Map(Text(nonempty=True)),
            'timeout': Integer(nonnull=True, default=30),
            'injections': Sequence(Text(nonempty=True)),
        },
        'internal': {
            'purpose': Enumeration('purge', nonempty=True),
        },
        'test': {
            'status': Enumeration('complete fail exception', nonempty=True),
            'result': Text(),
        }
    },
    polymorphic_on=Enumeration('http-request internal test', name='type', nonempty=True),
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
        created = DateTime(utc=True, readonly=True)
