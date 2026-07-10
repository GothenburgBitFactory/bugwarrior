import pytest

from .base import get_mock_service


@pytest.fixture
def make_service(request):
    def make(**overrides):
        return get_mock_service(
            request.module.SERVICE_CLASS, {**request.module.SERVICE_CONFIG, **overrides}
        )

    return make


@pytest.fixture
def service(make_service):
    return make_service()
