from datetime import datetime, timedelta

from scheme import UTC, current_timestamp
from spire.schema import *
from spire.support.logs import LogHelper

from platoon.support.scheduling import *

__all__ = ('Schedule', 'FixedSchedule', 'LogicalSchedule', 'MonthlySchedule',
    'WeeklySchedule')

log = LogHelper('platoon')
schema = Schema('platoon')

class Schedule(Model):
    """A task schedule."""

    class meta:
        polymorphic_on = 'type'
        schema = schema
        tablename = 'schedule'

    id = Identifier()
    type = Enumeration('fixed logical monthly weekly', nullable=False)
    name = Text(unique=True)

    @classmethod
    def create(cls, session, **attrs):
        instance = cls.polymorphic_create(attrs)

        session.add(instance)
        try:
            session.flush()
        except IntegrityError:
            raise OperationError(token='duplicate-schedule-name')
        else:
            return instance

    def next(self, *args, **params):
        occurrence = params.get('occurrence', None)
        now = current_timestamp()
        if not occurrence or occurrence < now:
            occurrence = now
        return self._next_occurrence(occurrence)

    def update(self, session, **attrs):
        self.update_with_mapping(attrs)
        try:
            session.flush()
        except IntegrityError:
            raise OperationError(token='duplicate-schedule-name')

class FixedSchedule(Schedule):
    """A fixed task schedule."""

    class meta:
        polymorphic_identity = 'fixed'
        schema = schema
        tablename = 'fixed_schedule'

    schedule_id = ForeignKey('schedule.id', nullable=False, primary_key=True, ondelete='CASCADE')
    anchor = DateTime(nullable=False, timezone=True)
    interval = Integer(nullable=False)

    def describe(self):
        return 'Every %d seconds' % self.interval

    def _next_occurrence(self, occurrence):
        occurrence = occurrence + timedelta(seconds=self.interval)
        if occurrence >= self.anchor:
            return occurrence
        else:
            return self.anchor

class LogicalSchedule(Schedule):
    """A logical task schedule."""

    class meta:
        polymorphic_identity = 'logical'
        schema = schema
        tablename = 'logical_schedule'

    schedule_id = ForeignKey('schedule.id', nullable=False, primary_key=True, ondelete='CASCADE')
    anchor = DateTime(timezone=True)
    month = Text()
    day = Text()
    weekday = Text()
    hour = Text()
    minute = Text()

    def describe(self):
        return 'logical'

    def _next_occurrence(self, occurrence):
        if self.anchor and occurrence < self.anchor:
            occurrence = self.anchor

        specification = (self.month, self.day, self.weekday, self.hour, self.minute)
        return Specification(specification).next(occurrence)

class MonthlySchedule(Schedule):
    """A monthly task schedule."""

    class meta:
        polymorphic_identity = 'monthly'
        schema = schema
        tablename = 'monthly_schedule'

    schedule_id = ForeignKey('schedule.id', nullable=False, primary_key=True, ondelete='CASCADE')
    anchor = DateTime(timezone=True, nullable=False)
    strategy = Enumeration('day weekday', nullable=False)
    interval = Integer(nullable=False)
    cached_next = DateTime(timezone=True)

    def describe(self):
        parts = []
        if self.interval == 1:
            parts.append('Monthly')
        else:
            parts.append('Every %d months' % self.interval)

        anchor = self.anchor
        if self.strategy == 'day':
            parts.append('day %d' % anchor.day)
        elif self.strategy == 'weekday':
            parts.append('%s' % describe_weekday_step(anchor))

        time = anchor.strftime('%Y-%m-%d %I:%M %p')
        if time[0] == '0':
            time = time[1:]

        parts.append('%s' % time)
        return ' / '.join(parts)

    def next(self, session, *args, **params):
        cache_results = params.get('cache_results', True)
        cached_next = self.cached_next
        if cached_next:
            if cached_next > current_timestamp():
                return cached_next
            occurrence = cached_next
        else:
            occurrence = self.anchor

        next = self._next_occurrence(occurrence)
        if cache_results:
            self.cached_next = next

        return next

    def _next_occurrence(self, occurrence):
        anchor = self.anchor
        if occurrence < anchor:
            occurrence = anchor
            #return anchor

        if self.strategy == 'day':
            specification = Specification(['*', str(anchor.day), '*',
                str(anchor.hour), str(anchor.minute)])
        elif self.strategy == 'weekday':
            specification = Specification(['*', '*', construct_weekday_step(anchor),
                str(anchor.hour), str(anchor.minute)])

        return specification.next_monthly_interval(self.interval, occurrence)

class WeeklySchedule(Schedule):
    """A weekly task schedule."""

    names = ('sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday')
    tokens = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')

    class meta:
        polymorphic_identity = 'weekly'
        schema = schema
        tablename = 'weekly_schedule'

    schedule_id = ForeignKey('schedule.id', nullable=False, primary_key=True, ondelete='CASCADE')
    anchor = DateTime(timezone=True, nullable=False)
    interval = Integer(nullable=False)
    sunday = Boolean(nullable=False, default=False)
    monday = Boolean(nullable=False, default=False)
    tuesday = Boolean(nullable=False, default=False)
    wednesday = Boolean(nullable=False, default=False)
    thursday = Boolean(nullable=False, default=False)
    friday = Boolean(nullable=False, default=False)
    saturday = Boolean(nullable=False, default=False)
    cached_next = DateTime(timezone=True)

    def describe(self):
        parts = []
        if self.interval == 1:
            parts.append('Weekly')
        else:
            parts.append('Every %d weeks' % self.interval)

        weekdays = []
        for name in self.names:
            if getattr(self, name):
                weekdays.append(name.capitalize())

        if len(weekdays) == 7:
            parts.append('all weekdays')
        else:
            parts.append(', '.join(weekdays))

        time = self.anchor.strftime('%Y-%m-%d %I:%M %p')
        if time[0] == '0':
            time = time[1:]

        parts.append('%s' % time)
        return ' / '.join(parts)

    def next(self, session, *args, **params):
        cache_results = params.get('cache_results', True)
        cached_next = self.cached_next
        if cached_next:
            if cached_next > current_timestamp() + timedelta(minutes=2):
                return cached_next
            occurrence = cached_next
        else:
            occurrence = self.anchor

        next = self._next_occurrence(occurrence)
        if cache_results:
            self.cached_next = next

        return next

    def _next_occurrence(self, occurrence):
        anchor = self.anchor.astimezone(UTC)
        occurrence = occurrence.astimezone(UTC)
        if occurrence < anchor:
            occurrence = anchor

        weekdays = []
        for i, token in enumerate(self.tokens):
            if getattr(self, token):
                weekdays.append(str(i + 1))

        specification = Specification(['*', '*', ';'.join(weekdays),
            str(anchor.hour), str(anchor.minute)])
        return specification.next_weekly_interval(self.interval,
            occurrence).replace(tzinfo=UTC)
