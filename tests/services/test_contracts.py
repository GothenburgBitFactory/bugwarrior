"""Ensure each service, and its test module, honors the service API."""

import importlib
from importlib.metadata import entry_points
import pathlib
import typing

import pytest

from bugwarrior.config import get_service

SERVICES = sorted(ep.name for ep in entry_points(group='bugwarrior.service'))

TEST_MODULES = sorted(
    path.stem
    for path in pathlib.Path(__file__).parent.glob('test_*.py')
    if path.stem != 'test_contracts'
)


def module_test_names(module):
    names = {name for name in vars(module) if name.startswith('test_')}
    for value in vars(module).values():
        if isinstance(value, type):
            names.update(name for name in dir(value) if name.startswith('test_'))
    return names


@pytest.mark.parametrize('module_name', TEST_MODULES)
def test_service_config_is_module_level(module_name):
    """
    Each service test module must define its base service section as a
    module-level SERVICE_CONFIG dict.
    """
    module = importlib.import_module(f'tests.services.{module_name}')

    assert isinstance(getattr(module, 'SERVICE_CONFIG', None), dict), (
        f'{module_name} does not define a module-level SERVICE_CONFIG dict'
    )


@pytest.mark.parametrize('module_name', TEST_MODULES)
def test_fake_data_is_not_class_state(module_name):
    """
    Fake API payloads must be module-level fixtures returning fresh objects,
    not mutable class attributes shared between tests.
    """
    module = importlib.import_module(f'tests.services.{module_name}')

    offenders = [
        f'{cls_name}.{name}'
        for cls_name, cls in vars(module).items()
        if isinstance(cls, type) and cls_name.startswith('Test')
        for name, value in vars(cls).items()
        if isinstance(value, (dict, list))
    ]
    assert not offenders, (
        f'{module_name} keeps mutable data on test classes: {offenders}'
    )


@pytest.mark.parametrize('required', ['test_to_taskwarrior', 'test_issues'])
@pytest.mark.parametrize('module_name', TEST_MODULES)
def test_core_service_methods_are_tested(module_name, required):
    """
    Each service test module must test to_taskwarrior() and issues().

    - When the API is accessed via requests, use the responses library to
    mock requests.
    - When the API is accessed via a third party library, substitute a fake
    implementation class for it.
    """
    module = importlib.import_module(f'tests.services.{module_name}')

    assert any(name.startswith(required) for name in module_test_names(module)), (
        f'{module_name} does not define a {required} test'
    )


@pytest.mark.parametrize('service_name', SERVICES)
def test_task_schema_matches_the_issue_class(service_name):
    """
    A service's TASK_SCHEMA must be the Task its ISSUE_CLASS actually returns.

    Nothing else checks this. TASK_SCHEMA is what tells bugwarrior which UDAs
    to write to the user's taskrc and which fields identify a task, and it is
    read without going through ISSUE_CLASS. Point it at the Task of another
    service and you get the wrong UDAs, and tasks stop matching.
    """
    service = get_service(service_name)
    mapped = typing.get_type_hints(service.ISSUE_CLASS.to_taskwarrior)['return']

    assert service.TASK_SCHEMA is mapped, (
        f'{service.__name__}.TASK_SCHEMA is {service.TASK_SCHEMA.__name__}, but '
        f'{service.ISSUE_CLASS.__name__}.to_taskwarrior returns {mapped.__name__}'
    )
