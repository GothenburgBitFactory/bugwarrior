import abc

import responses

from bugwarrior.config import schema

# ConfigTest is also re-exported so service tests can import it from here.
from ..base import ConfigTest


class AbstractServiceTest(abc.ABC):
    """Ensures that certain test methods are implemented for each service."""

    @abc.abstractmethod
    def test_to_taskwarrior(self):
        """Test Service.to_taskwarrior()."""
        raise NotImplementedError

    @abc.abstractmethod
    def test_issues(self):
        """
        Test Service.issues().

        - When the API is accessed via requests, use the responses library to
        mock requests.
        - When the API is accessed via a third party library, substitute a fake
        implementation class for it.
        """
        raise NotImplementedError


class ServiceTest(ConfigTest):
    GENERAL_CONFIG = {'annotation_length': 100, 'description_length': 100}
    SERVICE_CONFIG = {}

    @classmethod
    def setUpClass(cls):
        cls.maxDiff = None

    def get_mock_service(
        self,
        service_class,
        section='unspecified',
        config_overrides=None,
        general_overrides=None,
    ):
        options = {
            'general': {**self.GENERAL_CONFIG, 'targets': [section]},
            section: {**self.SERVICE_CONFIG.copy(), 'target': section},
        }
        if config_overrides:
            options[section].update(config_overrides)
        if general_overrides:
            options['general'].update(general_overrides)

        service_config = service_class.CONFIG_SCHEMA(**options[section])
        main_config = schema.MainSectionConfig(**options['general'])

        return service_class(service_config, main_config)

    @staticmethod
    def add_response(url, method='GET', **kwargs):
        responses.add(
            responses.Response(url=url, method=method, match_querystring=True, **kwargs)
        )
