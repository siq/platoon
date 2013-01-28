from spire.schema import *

from platoon.models.endpoint import Endpoint
from platoon.models.executor import *

__all__ = ('Queue',)

schema = Schema('platoon')

class Queue(Model):
    """A process queue."""

    class meta:
        schema = schema
        tablename = 'queue'

    id = Token(nullable=False, primary_key=True)
    subject = Token(nullable=False)
    name = Text()
    status = Enumeration('active inactive', nullable=False, default='active')
    endpoint_id = ForeignKey('endpoint.id')

    endpoint = relationship(Endpoint, cascade='all,delete-orphan', single_parent=True)

    def assign_executor_endpoint(self, session):
        return self.query_executor_endpoints(session).first()

    @classmethod
    def create(cls, session, endpoint=None, **attrs):
        queue = cls(**attrs)
        if endpoint:
            queue.endpoint = Endpoint.polymorphic_create(endpoint)

        session.add(queue)
        return queue

    def query_executor_endpoints(self, session, active_only=True):
        query = session.query(ExecutorEndpoint).filter_by(subject=self.subject)
        if active_only:
            query = query.join(Executor).filter(Executor.status=='active')
        return query

    def update(self, session, **attrs):
        if 'endpoint' in attrs:
            endpoint = attrs.pop('endpoint')
            if endpoint:
                if self.endpoint:
                    self.endpoint.update_with_mapping(endpoint)
                else:
                    self.endpoint = Endpoint.polymorphic_create(endpoint)
            else:
                self.endpoint = None

        self.update_with_mapping(attrs)
