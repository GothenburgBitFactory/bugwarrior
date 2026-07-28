"""Ensure each service's test module exercises the core service methods."""

import importlib
import pathlib

import pytest

TEST_MODULES = sorted(
    path.stem
    for path in pathlib.Path(__file__).parent.glob("test_*.py")
    if path.stem != "test_contracts"
)


def module_test_names(module):
    names = {name for name in vars(module) if name.startswith("test_")}
    for value in vars(module).values():
        if isinstance(value, type):
            names.update(name for name in dir(value) if name.startswith("test_"))
    return names


@pytest.mark.parametrize("module_name", TEST_MODULES)
def test_service_config_is_module_level(module_name):
    """
    Each service test module must define its base service section as a
    module-level SERVICE_CONFIG dict.
    """
    module = importlib.import_module(f"tests.services.{module_name}")

    assert isinstance(getattr(module, "SERVICE_CONFIG", None), dict), (
        f"{module_name} does not define a module-level SERVICE_CONFIG dict"
    )


@pytest.mark.parametrize("module_name", TEST_MODULES)
def test_fake_data_is_not_class_state(module_name):
    """
    Fake API payloads must be module-level fixtures returning fresh objects,
    not mutable class attributes shared between tests.
    """
    module = importlib.import_module(f"tests.services.{module_name}")

    offenders = [
        f"{cls_name}.{name}"
        for cls_name, cls in vars(module).items()
        if isinstance(cls, type) and cls_name.startswith("Test")
        for name, value in vars(cls).items()
        if isinstance(value, (dict, list))
    ]
    assert not offenders, (
        f"{module_name} keeps mutable data on test classes: {offenders}"
    )


@pytest.mark.parametrize("required", ["test_to_taskwarrior", "test_issues"])
@pytest.mark.parametrize("module_name", TEST_MODULES)
def test_core_service_methods_are_tested(module_name, required):
    """
    Each service test module must test to_taskwarrior() and issues().

    - When the API is accessed via requests, use the responses library to
    mock requests.
    - When the API is accessed via a third party library, substitute a fake
    implementation class for it.
    """
    module = importlib.import_module(f"tests.services.{module_name}")

    assert any(name.startswith(required) for name in module_test_names(module)), (
        f"{module_name} does not define a {required} test"
    )
