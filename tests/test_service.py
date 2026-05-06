import abc
import pathlib
from pathlib import Path
import re
import unittest.mock

from bugwarrior import services
from bugwarrior.config import validation
from bugwarrior.config.load import format_config

from .base import ConfigTest, DumbService

LONG_MESSAGE = """\
Some message that is over 100 characters. This message is so long it's
going to fill up your floppy disk taskwarrior backup. Actually it's not
that long.""".replace('\n', ' ')


class ServiceBase(ConfigTest):
    def setUp(self):
        super().setUp()
        self.config = {'general': {'targets': ['test']}, 'test': {'service': 'test'}}

    def makeService(self):
        with unittest.mock.patch(
            'bugwarrior.config.validation.get_service', lambda x: DumbService
        ):
            formatted = format_config(self.config)
            conf = validation.validate_config(formatted, 'general', 'configpath')
        return DumbService(conf.service_configs[0], conf.main)

    def makeIssue(self):
        service = self.makeService()
        return service.get_issue_for_record({})

    def checkArchitecture(
        self, klass: abc.ABCMeta, method_allowlist: set[str] | None = None
    ):
        """
        Bidirectional communication between the base classes and their children
        has been a source of complication as changes to any part of the
        circular data flow can create unpredictable side-effects. The concrete
        methods of the base classes exist as utilities for children to call;
        they should not call the abstract methods which children implement.

        Here, we cheaply check that the names of the abstract methods only
        appear once. This should ensure that these methods are declared here
        but not called.
        """
        base = Path(services.__file__).read_text()

        for method in klass.__abstractmethods__ - (method_allowlist or set()):
            references = re.findall(rf'{method}\(', base)
            self.assertEqual(len(references), 1, references)


class TestService(ServiceBase):
    def test_architecture(self):
        self.checkArchitecture(services.Service, {"get_keyring_service"})

    def test_build_annotations_default(self):
        service = self.makeService()

        annotations = service.build_annotations(
            (('some_author', LONG_MESSAGE),), 'example.com'
        )
        self.assertEqual(
            annotations,
            ['@some_author - Some message that is over 100 characters. Thi...'],
        )

    def test_build_annotations_limited(self):
        self.config['general']['annotation_length'] = '20'
        service = self.makeService()

        annotations = service.build_annotations(
            (('some_author', LONG_MESSAGE),), 'example.com'
        )
        self.assertEqual(annotations, ['@some_author - Some message that is...'])

    def test_build_annotations_limitless(self):
        self.config['general']['annotation_length'] = None
        service = self.makeService()

        annotations = service.build_annotations(
            (('some_author', LONG_MESSAGE),), 'example.com'
        )
        self.assertEqual(annotations, [f'@some_author - {LONG_MESSAGE}'])

    def test_api_incompatibility_error(self):
        with unittest.mock.patch.object(
            DumbService, 'API_VERSION', new=services.LATEST_API_VERSION + 1
        ):
            with self.assertRaisesRegex(ValueError, "Incompatible Service"):
                self.makeService()

    def test_api_latest_version(self):
        basedir = pathlib.Path(__file__).parent.parent
        with open(basedir / 'bugwarrior/docs/other-services/api.rst', 'r') as f:
            header = f.readline().strip('\n')
            match = re.fullmatch(r'Python API v(?P<version>[0-9]+\.[0-9]+)', header)
            latest_documented = float(match.groupdict()['version'])

        self.assertEqual(latest_documented, services.LATEST_API_VERSION)


class TestIssue(ServiceBase):
    def test_architecture(self):
        self.checkArchitecture(services.Issue)

    def test_build_default_description_default(self):
        issue = self.makeIssue()

        description = issue.build_default_description(LONG_MESSAGE)
        self.assertEqual(description, '(bw)Is# - Some message that is over 100 chara')

    def test_build_default_description_limited(self):
        self.config['general']['description_length'] = '20'
        issue = self.makeIssue()

        description = issue.build_default_description(LONG_MESSAGE)
        self.assertEqual(description, '(bw)Is# - Some message that is')

    def test_build_default_description_limitless(self):
        self.config['general']['description_length'] = None
        issue = self.makeIssue()

        description = issue.build_default_description(LONG_MESSAGE)
        self.assertEqual(description, f'(bw)Is# - {LONG_MESSAGE}')

    def test_get_tags_from_labels_normalization(self):
        self.config['test']['import_labels_as_tags'] = True
        issue = self.makeIssue()

        self.assertEqual(issue.get_tags_from_labels(['needs work']), ['needs_work'])
