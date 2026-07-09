"""Ensure each service's test module exercises the core service methods."""

import importlib
import pathlib

import pytest

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
