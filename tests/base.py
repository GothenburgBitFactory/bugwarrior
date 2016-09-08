import mock
import shutil
import os
import os.path
import tempfile
import unittest

import responses


class AbstractServiceTest(object):
    """ Ensures that certain test methods are implemented for each service. """
    def test_to_taskwarrior(self):
        """ Test Service.to_taskwarrior(). """
        raise NotImplementedError

    def test_issues(self):
        """
        Test Service.issues().

        - When the API is accessed via requests, use the responses library to
        mock requests.
        - When the API is accessed via a third party library, substitute a fake
        implementation class for it.
        """
        raise NotImplementedError


class ServiceTest(unittest.TestCase):
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
        options['general']['taskrc'] = self.taskrc

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

    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.mkdtemp(prefix='bugwarrior')
        cls.taskrc = os.path.join(cls.tempdir, 'taskrc')
        lists_path = os.path.join(cls.tempdir, 'lists')
        os.mkdir(lists_path)
        with open(cls.taskrc, 'w+') as fout:
            fout.write('data.location=%s\n' % lists_path)

        # Clear the environment of external settings.
        os.environ['TASKRC'] = cls.taskrc
        os.environ.pop('TASKDATA', None)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tempdir, ignore_errors=True)

    @staticmethod
    def add_response(url, **kwargs):
        responses.add(responses.GET, url, match_querystring=True, **kwargs)
