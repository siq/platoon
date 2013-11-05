"""refactor_schedule

Revision: 1250afd87885
Revises: f2bce15746e
Created: 2013-11-05 11:27:42.420647
"""

revision = '1250afd87885'
down_revision = 'f2bce15746e'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint, CheckConstraint, text
from sqlalchemy.dialects import postgresql

def upgrade():
    connection = op.get_bind()
    schedules = list(connection.execute('select * from schedule'))

    op.create_table('fixed_schedule',
        Column('schedule_id', UUIDType(), nullable=False),
        Column('anchor', DateTimeType(timezone=True), nullable=False),
        Column('interval', IntegerType(), nullable=False),
        ForeignKeyConstraint(['schedule_id'], ['schedule.id']),
        PrimaryKeyConstraint('schedule_id')
    )
    op.create_table('weekly_schedule',
        Column('schedule_id', UUIDType(), nullable=False),
        Column('anchor', DateTimeType(timezone=True), nullable=False),
        Column('interval', IntegerType(), nullable=False),
        Column('sunday', BooleanType(), nullable=False),
        Column('monday', BooleanType(), nullable=False),
        Column('tuesday', BooleanType(), nullable=False),
        Column('wednesday', BooleanType(), nullable=False),
        Column('thursday', BooleanType(), nullable=False),
        Column('friday', BooleanType(), nullable=False),
        Column('saturday', BooleanType(), nullable=False),
        ForeignKeyConstraint(['schedule_id'], ['schedule.id']),
        PrimaryKeyConstraint('schedule_id')
    )
    op.create_table('logical_schedule',
        Column('schedule_id', UUIDType(), nullable=False),
        Column('anchor', DateTimeType(timezone=True), nullable=True),
        Column('month', TextType(), nullable=True),
        Column('day', TextType(), nullable=True),
        Column('weekday', TextType(), nullable=True),
        Column('hour', TextType(), nullable=True),
        Column('minute', TextType(), nullable=True),
        ForeignKeyConstraint(['schedule_id'], ['schedule.id']),
        PrimaryKeyConstraint('schedule_id')
    )
    op.create_table('monthly_schedule',
        Column('schedule_id', UUIDType(), nullable=False),
        Column('anchor', DateTimeType(timezone=True), nullable=False),
        Column('strategy', EnumerationType(), nullable=False),
        Column('interval', IntegerType(), nullable=False),
        ForeignKeyConstraint(['schedule_id'], ['schedule.id']),
        PrimaryKeyConstraint('schedule_id')
    )

    op.drop_column('schedule', 'interval')
    op.drop_column('schedule', 'anchor')
    op.drop_column('schedule', 'schedule')

    op.add_column('schedule', Column('type', EnumerationType(), nullable=True))
    op.execute("update schedule set type = 'fixed'")
    op.alter_column('schedule', 'type', nullable=False)

    fixed_schedule_insert = text("insert into fixed_schedule (schedule_id, anchor, interval) "
        "values (:id, :anchor, :interval)")

    for row in schedules:
        connection.execute(fixed_schedule_insert, id=row.id, anchor=row.anchor, interval=row.interval)

def downgrade():
    op.add_column(u'schedule', Column(u'schedule', TEXT(), nullable=False))
    op.add_column(u'schedule', Column(u'anchor', postgresql.TIMESTAMP(timezone=True), nullable=False))
    op.add_column(u'schedule', Column(u'interval', INTEGER(), nullable=False))
    op.drop_column(u'schedule', 'type')
    op.drop_table('monthly_schedule')
    op.drop_table('logical_schedule')
    op.drop_table('weekly_schedule')
    op.drop_table('fixed_schedule')
