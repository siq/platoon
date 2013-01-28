from datetime import datetime, timedelta

from scheme import UTC, current_timestamp
from spire.schema import *
from spire.support.logs import LogHelper
from sqlalchemy.sql import bindparam, text

from platoon.models.subscribedtask import SubscribedTask

__all__ = ('Event',)

log = LogHelper('platoon')
schema = Schema('platoon')

class Event(Model):
    """An event."""

    class meta:
        schema = schema
        tablename = 'event'

    id = Identifier()
    topic = Token(nullable=False)
    aspects = Hstore()
    status = Enumeration('pending completed', nullable=False, default='pending')
    occurrence = DateTime(timezone=True)

    HSTORE_FILTER = text(':aspects @> subscribed_task.aspects',
        bindparams=[bindparam('aspects', type_=aspects.type)])

    @classmethod
    def create(cls, session, topic, aspects=None):
        event = Event(topic=topic, aspects=aspects, occurrence=datetime.now(UTC))
        session.add(event)
        return event

    def collate_tasks(self, session):
        model = SubscribedTask
        return (session.query(model).with_lockmode('update')
            .filter(model.topic==self.topic)
            .filter((model.activation_limit == None) | (model.activations < model.activation_limit))
            .filter(self.HSTORE_FILTER | (model.aspects == None))
            .params(aspects=(self.aspects or {})))

    def describe(self):
        aspects = {'topic': self.topic}
        if self.aspects:
            aspects.update(self.aspects)
        return aspects

    @classmethod
    def process_events(cls, session):
        for event in session.query(cls).with_lockmode('update').filter_by(status='pending'):
            event.schedule_tasks(session)
        else:
            session.commit()

    @classmethod
    def purge(cls, session, lifetime):
        delta = datetime.now(UTC) - timedelta(days=lifetime)
        session.query(cls).filter(cls.status == 'completed', cls.occurrence < delta).delete()

    def schedule_tasks(self, session):
        description = self.describe()
        for task in self.collate_tasks(session):
            task.activate(session, description)

        self.status = 'completed'
