from datetime import datetime, timedelta

from scheme import UTC, current_timestamp
from spire.schema import *
from spire.support.logs import LogHelper

__all__ = ('Schedule',)

log = LogHelper('platoon')
schema = Schema('platoon')

class Schedule(Model):
    """A task schedule."""

    class meta:
        schema = schema
        tablename = 'schedule'

    id = Identifier()
    name = Text(unique=True)
    schedule = Enumeration('fixed', nullable=False)
    anchor = DateTime(nullable=False, timezone=True)
    interval = Integer(nullable=False)

    def next(self, occurrence):
        occurrence = self._next_occurrence(occurrence)

        now = datetime.now(UTC)
        if occurrence >= now:
            return occurrence
        else:
            return self._next_occurrence(now)

    def _next_occurrence(self, occurrence):
        schedule = self.schedule
        if schedule == 'fixed':
            return self._next_fixed(occurrence)

    def _next_fixed(self, occurrence):
        occurrence = occurrence + timedelta(seconds=self.interval)
        if occurrence >= self.anchor:
            return occurrence
        else:
            return self.anchor
