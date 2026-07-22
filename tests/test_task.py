from pydantic import Field, ValidationError
import pytest

from bugwarrior.task import IssueDatetime, Task, Udas


class SampleUdas(Udas):
    UNIQUE_KEY = ("sampleurl",)

    samplenumber: int | None = Field(default=None, title="Sample Number")
    sampleurl: str | None = Field(default=None, title="Sample URL")
    samplecreated: IssueDatetime = Field(default=None, title="Sample Created")


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
    # Only explicitly set scalar fields are emitted, so legacy sparse records
    # are preserved; tags is always present.
    assert Task(project='foundation').to_taskwarrior_data() == {
        'project': 'foundation',
        'tags': [],
    }


def test_udas_are_flattened_and_always_emitted():
    task = SampleTask(
        project='foundation',
        udas=SampleUdas(sampleurl='http://example.com', samplenumber=7),
    )

    assert task.to_taskwarrior_data() == {
        'project': 'foundation',
        'tags': [],
        # every UDA is emitted, even the unset one
        'samplenumber': 7,
        'sampleurl': 'http://example.com',
        'samplecreated': None,
    }


def test_get_udas_is_derived_from_the_udas_model():
    assert SampleUdas.get_udas() == {
        'samplenumber': {'type': 'numeric', 'label': 'Sample Number'},
        'sampleurl': {'type': 'string', 'label': 'Sample URL'},
        'samplecreated': {'type': 'date', 'label': 'Sample Created'},
    }


def test_base_udas_has_no_udas():
    assert Udas.get_udas() == {}


def test_get_unique_key():
    assert SampleUdas.get_unique_key() == ("sampleurl",)


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError):
        SampleTask(udas=SampleUdas(), bogus='nope')
