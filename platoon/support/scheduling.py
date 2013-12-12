from scheme.timezone import current_timestamp, UTC
from datetime import datetime, timedelta, time

QUANTITIES = {
    'minute': (0, 59),
    'hour': (0, 23),
    'day': (1, 31),
    'week': (1, 5),
    'month': (1, 12),
}

STEPS = ['', 'first', 'second', 'third', 'fourth', 'fifth']

def advance_by_month(value, interval):
    for _ in range(interval):
        if value.month == 12:
            value = value.replace(value.year + 1, 1, value.day)
        else:
            value = value.replace(value.year, value.month + 1, value.day)
    else:
        return value

def advance_by_week(value, interval):
    for _ in range(interval):
        value += timedelta(days=7)
    return value

def construct_weekday_step(occurrence):
    return '%s/%s' % (occurrence.isoweekday(), identify_weekday_step(occurrence))

def describe_weekday_step(occurrence):
    step = STEPS[identify_weekday_step(occurrence)]
    return '%s %s' % (step, occurrence.strftime('%A'))

def identify_weekday_step(value):
    if isinstance(value, datetime):
        value = value.date()

    weekday = value.isoweekday()
    step = 0

    day = value.replace(day=1)
    while True:
        if day.isoweekday() == weekday:
            step += 1
        if day.day == value.day:
            return step
        else:
            day += timedelta(days=1)

def validate_range(quantity, value):
    try:
        minimum, maximum = QUANTITIES[quantity]
    except KeyError:
        raise ValueError(quantity)

    if value[0] == '*':
        if value == '*':
            step = 1
        else:
            step = int(value[2:])
        return list(range(minimum, maximum + 1, step))

    candidates = set()
    for candidate in value.split(','):
        if '-' in candidate:
            if '/' in candidate:
                candidate, step = candidate.split('/')
            else:
                step = 1
            start, stop = candidate.split('-')
            for i in range(int(start), int(stop) + 1, int(step)):
                candidates.add(i)
        else:
            candidates.add(int(candidate))

    candidates = list(sorted(candidates))
    if min(candidates) < minimum:
        raise ValueError(value)
    elif max(candidates) > maximum:
        raise ValueError(value)
    else:
        return candidates

def validate_weekday(value):
    candidates = {}
    if not value or value == '*':
        return None

    for candidate in value.split(';'):
        if '/' in candidate:
            candidate, steps = candidate.split('/')
            steps = validate_range('week', steps)
        else:
            steps = [1, 2, 3, 4, 5]

        candidate = int(candidate)
        if 1 <= candidate <= 7:
            if candidate not in candidates:
                candidates[candidate] = steps
            else:
                raise ValueError(value)
        else:
            raise ValueError(value)

    return candidates

class Specification(object):
    """A schedule specification."""

    def __init__(self, specification):
        if isinstance(specification, basestring):
            month, day, weekday, hour, minute = specification.strip().split(' ')
        else:
            month, day, weekday, hour, minute = specification

        self.month = validate_range('month', month or '*')
        self.day = validate_range('day', day or '*')
        self.weekday = validate_weekday(weekday or '*')
        self.hour = validate_range('hour', hour or '*')
        self.minute = validate_range('minute', minute or '*')

    def generate(self, count, occurrence=None):
        for i in range(count):
            occurrence = self.next(occurrence)
            yield occurrence

    def next(self, occurrence=None):
        if not occurrence:
            occurrence = current_timestamp()

        occurrence = occurrence.replace(second=0, microsecond=0)
        if self._check_date(occurrence):
            candidate = self._next_time(occurrence)
            if candidate:
                return candidate

        occurrence = occurrence.replace(hour=0, minute=0)
        while True:
            occurrence += timedelta(days=1)
            if self._check_date(occurrence):
                candidate = self._next_time(occurrence)
                if candidate:
                    return candidate

    def next_monthly_interval(self, interval, occurrence=None):
        now = current_timestamp()
        if not occurrence:
            occurrence = now

        candidate = occurrence.replace(day=1, hour=0, minute=0)
        current_month_threshold = now.replace(day=1, hour=0, minute=1)
        while candidate < current_month_threshold:
            candidate = advance_by_month(candidate, interval)

        next = self.next(candidate)
        if next < now:
            next = self.next(advance_by_month(candidate, interval))
        return next

    def next_weekly_interval(self, interval, occurrence=None):
        now = current_timestamp()
        if not occurrence:
            occurrence = now

        if occurrence > now and self._check_date(occurrence):
            if occurrence.hour in self.hour and occurrence.minute in self.minute:
                return occurrence

        week = Week.from_date(occurrence)
        candidate = self.next(occurrence)
        if candidate in week and candidate > now:
            return candidate

        candidate = datetime.combine(week.start, time(0, 0, 0)).replace(
                tzinfo=occurrence.tzinfo)
        while now > candidate:
            candidate = advance_by_week(candidate, interval)
            week = Week.from_date(candidate)
            if now in week:
                candidate = now
                break

        return self.next(candidate)

    def _check_date(self, value):
        if value.month not in self.month:
            return False
        if value.day not in self.day:
            return False
        if not self.weekday:
            return True

        weekday = value.isoweekday()
        if weekday not in self.weekday:
            return False

        step = identify_weekday_step(value)
        return step in self.weekday[weekday]

    def _next_time(self, value):
        candidate = value.replace(second=0, microsecond=0)
        while candidate.date() == value.date():
            if candidate.hour not in self.hour:
                if candidate.hour < 23:
                    candidate = candidate.replace(hour=candidate.hour + 1, minute=0)
                else:
                    return
            elif candidate.minute not in self.minute:
                candidate += timedelta(minutes=1)
            else:
                return candidate

class Week(object):
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __contains__(self, value):
        if isinstance(value, datetime):
            value = value.date()
        return (self.start <= value <= self.end)

    @classmethod
    def from_date(cls, value):
        if isinstance(value, datetime):
            value = value.date()

        start = value
        while start.isoweekday() != 7:
            start -= timedelta(days=1)

        end = value
        while end.isoweekday() != 6:
            end += timedelta(days=1)

        return cls(start, end)
