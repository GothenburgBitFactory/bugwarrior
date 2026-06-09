import abc
import pathlib
from pathlib import Path
import re
import unittest.mock

from bugwarrior import services
from bugwarrior.config import ServiceConfig, schema

from .base import ConfigTest, DumbConfig, DumbService

LONG_MESSAGE = """\
Some message that is over 100 characters. This message is so long it's
going to fill up your floppy disk taskwarrior backup. Actually it's not
that long.""".replace('\n', ' ')


class ServiceBase(ConfigTest):
    def makeService(self, general_overrides=None, config_overrides=None):
        main_config = schema.MainSectionConfig(
            targets=['test'], **(general_overrides or {})
        )
        service_config = DumbConfig(target='test', **(config_overrides or {}))
        return DumbService(service_config, main_config)

    def makeIssue(self, general_overrides=None, config_overrides=None):
        service = self.makeService(general_overrides, config_overrides)
        return service.get_issue_for_record({})

    def checkArchitecture(self, klass: abc.ABCMeta):
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

        for method in klass.__abstractmethods__:
            references = re.findall(rf'{method}\(', base)
            self.assertEqual(len(references), 1, references)


class TestService(ServiceBase):
    def test_architecture(self):
        self.checkArchitecture(services.Service)

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
        service = self.makeService(general_overrides={'annotation_length': '20'})

        annotations = service.build_annotations(
            (('some_author', LONG_MESSAGE),), 'example.com'
        )
        self.assertEqual(annotations, ['@some_author - Some message that is...'])

    def test_build_annotations_limitless(self):
        service = self.makeService(general_overrides={'annotation_length': None})

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

    def test_api_v1_keyring_service_backwards_compatibility(self):
        class LegacyService:
            API_VERSION = 1.0

            @staticmethod
            def get_keyring_service(config):
                return f'legacy://{config.target}'

        service_config = ServiceConfig(service='legacy', target='legacy-target')
        with unittest.mock.patch(
            'bugwarrior.config.schema.get_service', lambda _: LegacyService
        ):
            self.assertEqual(service_config.keyring_service, 'legacy://legacy-target')


class TestIssue(ServiceBase):
    def test_architecture(self):
        self.checkArchitecture(services.Issue)

    def test_build_default_description_default(self):
        issue = self.makeIssue()

        description = issue.build_default_description(LONG_MESSAGE)
        self.assertEqual(description, '(bw)Is# - Some message that is over 100 chara')

    def test_build_default_description_limited(self):
        issue = self.makeIssue(general_overrides={'description_length': '20'})

        description = issue.build_default_description(LONG_MESSAGE)
        self.assertEqual(description, '(bw)Is# - Some message that is')

    def test_build_default_description_limitless(self):
        issue = self.makeIssue(general_overrides={'description_length': None})

        description = issue.build_default_description(LONG_MESSAGE)
        self.assertEqual(description, f'(bw)Is# - {LONG_MESSAGE}')

    def test_get_tags_from_labels_normalization(self):
        issue = self.makeIssue(config_overrides={'import_labels_as_tags': True})

        self.assertEqual(issue.get_tags_from_labels(['needs work']), ['needs_work'])
