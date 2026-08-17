import datetime

from pydantic import Field, ValidationError
import pytest
from taskw import TaskWarriorShellout

from bugwarrior.task import Duration, IssueDatetime, Task, Udas


class SampleUdas(Udas):
    UNIQUE_KEY = ("sampleurl",)

    samplenumber: int | None = Field(default=None, title="Sample Number")
    sampleurl: str | None = Field(default=None, title="Sample URL")
    samplecreated: IssueDatetime = Field(default=None, title="Sample Created")
    samplespent: Duration = Field(default=None, title="Sample Spent")


class SampleTask(Task):
    udas: SampleUdas


def test_generic_fields_are_coerced():
    task = Task(priority='', status='PENDING', due='2026-05-20')

    data = task.to_taskwarrior_data()
    assert data['priority'] is None  # blank priority means no priority
    assert data['status'] == 'pending'
    assert data['due'].tzinfo is not None  # naive input gets UTC
    assert data['due'].microsecond == 0  # sub-second precision dropped


def test_unset_generic_fields_are_omitted():
    # Only explicitly set fields are emitted, so legacy sparse records are
    # preserved.
    assert Task(project='foundation').to_taskwarrior_data() == {'project': 'foundation'}


def test_udas_are_flattened_and_always_emitted():
    task = SampleTask(
        project='foundation',
        udas=SampleUdas(sampleurl='http://example.com', samplenumber=7),
    )

    assert task.to_taskwarrior_data() == {
        'project': 'foundation',
        # every UDA is emitted, even the unset one
        'samplenumber': 7,
        'sampleurl': 'http://example.com',
        'samplecreated': None,
        'samplespent': None,
    }


def test_get_udas_is_derived_from_the_udas_model():
    assert SampleUdas.get_udas() == {
        'samplenumber': {'type': 'numeric', 'label': 'Sample Number'},
        'sampleurl': {'type': 'string', 'label': 'Sample URL'},
        'samplecreated': {'type': 'date', 'label': 'Sample Created'},
        'samplespent': {'type': 'duration', 'label': 'Sample Spent'},
    }


# Taskwarrior rejects Python's own "3:30:00" rendering of a timedelta, which is
# how https://github.com/GothenburgBitFactory/bugwarrior/pull/967 arose. It
# reads ISO 8601 but saves it in days, hours, minutes and seconds, so that is
# what we write: see test_duration_round_trips_through_taskwarrior.
DURATIONS = [
    (datetime.timedelta(hours=3.5), 'PT3H30M'),
    (datetime.timedelta(0), 'PT0S'),  # a zero duration is still a duration
    (datetime.timedelta(days=1, hours=1, minutes=1, seconds=1), 'P1DT1H1M1S'),
    (datetime.timedelta(days=7), 'P7D'),  # whole days carry no time part
    (datetime.timedelta(hours=2), 'PT2H'),
    (datetime.timedelta(seconds=90), 'PT1M30S'),
    (datetime.timedelta(seconds=1.6), 'PT1S'),  # fractions are rejected
    (datetime.timedelta(seconds=-60), 'PT0S'),  # negatives are rejected
]


@pytest.mark.parametrize(('spent', 'expected'), [*DURATIONS, (None, None)])
def test_duration_is_emitted_as_iso_8601(spent, expected):
    task = SampleTask(udas=SampleUdas(samplespent=spent))

    assert task.to_taskwarrior_data()['samplespent'] == expected


@pytest.mark.parametrize(('spent', 'expected'), DURATIONS)
def test_duration_round_trips_through_taskwarrior(config_environment, spent, expected):
    """
    Taskwarrior must store a duration exactly as we write it.

    It accepts several forms but saves only one of them. Write another one
    and the task looks changed on every sync, and is updated again and again.
    """
    emitted = SampleTask(udas=SampleUdas(samplespent=spent)).to_taskwarrior_data()[
        'samplespent'
    ]
    tw = TaskWarriorShellout(
        config_filename=str(config_environment.taskrc),
        config_overrides={'uda': {'samplespent': {'type': 'duration'}}},
        marshal=True,
    )
    tw.task_add(description='round trip', samplespent=emitted)

    _, task = tw.get_task(description='round trip')

    assert emitted == expected
    assert task['samplespent'] == emitted


def test_base_udas_has_no_udas():
    assert Udas.get_udas() == {}


def test_task_exposes_the_udas_of_its_udas_model():
    assert SampleTask.udas_model() is SampleUdas
    assert SampleTask.get_udas() == SampleUdas.get_udas()
    assert Task.get_udas() == {}


def test_get_unique_key():
    assert SampleTask.get_unique_key() == ("sampleurl",)


def test_unique_identifier_covers_only_the_unique_key():
    task = SampleTask(
        project='foundation',
        udas=SampleUdas(sampleurl='http://example.com', samplenumber=7),
    )

    # Sorted keys, so the identifier is stable regardless of field order, and
    # limited to the unique key, so unrelated edits do not orphan the task.
    assert task.unique_identifier() == '{"sampleurl": "http://example.com"}'


def test_a_schema_without_a_unique_key_is_an_error():
    with pytest.raises(AttributeError):
        Task.get_unique_key()

    with pytest.raises(AttributeError):
        Task().unique_identifier()


def test_unique_identifier_is_not_emitted_to_taskwarrior():
    # It identifies the task for matching; it is not a field of the record.
    assert 'unique_identifier' not in Task().to_taskwarrior_data()


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError):
        SampleTask(udas=SampleUdas(), bogus='nope')
