from mesh.standard import *
from scheme import *

Endpoint = Structure(
    structure={
        'http': {
            'url': Text(nonempty=True),
            'method': Text(nonnull=True, default='POST'),
            'mimetype': Text(nonnull=True, default='application/json'),
            'headers': Map(Text(nonempty=True), nonnull=True),
            'info': Field(),
        }
    },
    polymorphic_on=Enumeration('http', name='type', nonempty=True),
    nonnull=True)

class Executor(Resource):
    """A queue executor."""

    name = 'executor'
    version = 1
    requests = 'create delete get put query update'

    class schema:
        id = Token(nonempty=True, oncreate=True, operators='equal')
        name = Text(operators='equal')
        status = Enumeration('active inactive disabled', nonnull=True, default='active')
        endpoints = Map(Endpoint, nonnull=True)
