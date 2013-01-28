from spire.schema import *
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm.collections import attribute_mapped_collection

from platoon.models.endpoint import Endpoint

__all__ = ('Executor', 'ExecutorEndpoint')

schema = Schema('platoon')

class Executor(Model):
    """An executor."""

    class meta:
        schema = schema
        tablename = 'executor'

    id = Token(nullable=False, primary_key=True)
    name = Text()
    status = Enumeration('active inactive disabled', nullable=False, default='active')

    endpoints = association_proxy('executor_endpoints', 'endpoint',
        creator=lambda k, v: ExecutorEndpoint(subject=k, endpoint=v))

    @classmethod
    def create(cls, session, endpoints=None, **attrs):
        executor = cls(**attrs)
        if endpoints:
            for subject, endpoint in endpoints.iteritems():
                executor.endpoints[subject] = Endpoint.polymorphic_create(endpoint)
        
        session.add(executor)
        return executor

    def update(self, session, **attrs):
        pass

class ExecutorEndpoint(Model):
    """An executor endpoint."""

    class meta:
        constraints = [UniqueConstraint('executor_id', 'endpoint_id', 'subject')]
        schema = schema
        tablename = 'executor_endpoint'

    id = Identifier()
    executor_id = ForeignKey('executor.id', nullable=False, ondelete='CASCADE')
    endpoint_id = ForeignKey('endpoint.id', nullable=False)
    subject = Text(nullable=False)

    executor = relationship(Executor, backref=backref('executor_endpoints',
        collection_class=attribute_mapped_collection('subject'),
        cascade='all,delete-orphan', passive_deletes=True))
    endpoint = relationship(Endpoint, cascade='all,delete-orphan', single_parent=True)

