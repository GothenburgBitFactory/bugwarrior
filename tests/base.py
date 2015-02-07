import mock
import unittest2


class ServiceTest(unittest2.TestCase):
    GENERAL_CONFIG = {
        'annotation_length': 100,
        'description_length': 100,
    }
    SERVICE_CONFIG = {
    }

    def get_mock_service(
        self, service, section='unspecified',
        config_overrides=None, general_overrides=None
    ):
        options = {
            'general': self.GENERAL_CONFIG.copy(),
            section: self.SERVICE_CONFIG.copy(),
        }
        if config_overrides:
            options[section].update(config_overrides)
        if general_overrides:
            options['general'].update(general_overrides)

        def has_option(section, name):
            try:
                return options[section][name]
            except KeyError:
                return False

        def get_option(section, name):
            return options[section][name]

        def get_int(section, name):
            return int(get_option(section, name))

        config = mock.Mock()
        config.has_option = mock.Mock(side_effect=has_option)
        config.get = mock.Mock(side_effect=get_option)
        config.getint = mock.Mock(side_effect=get_int)

        service = service(config, 'general', section)

        return service
