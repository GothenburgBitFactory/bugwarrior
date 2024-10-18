import re
import unittest.mock

import typing_extensions

from bugwarrior import config, services
from bugwarrior.config import schema

from .base import ConfigTest

LONG_MESSAGE = """\
Some message that is over 100 characters. This message is so long it's
going to fill up your floppy disk taskwarrior backup. Actually it's not
that long.""".replace('\n', ' ')


class DumbConfig(config.ServiceConfig):
    service: typing_extensions.Literal['test']

    import_labels_as_tags: bool = False
    label_template: str = '{{label}}'


class DumbIssue(services.Issue):
    """
    Implement the required methods but they shouldn't be called.
    """

    def get_default_description(self):
        raise NotImplementedError

    def to_taskwarrior(self):
        raise NotImplementedError


class DumbService(services.Service):
    """
    Implement the required methods but they shouldn't be called.
    """
    ISSUE_CLASS = DumbIssue
    CONFIG_SCHEMA = DumbConfig

    def get_owner(self, issue):
        raise NotImplementedError

    def issues(self):
        raise NotImplementedError


class ServiceBase(ConfigTest):

    def setUp(self):
        super().setUp()
        self.config = {
            'general': {
                'targets': ['test'],
                'interactive': 'false',
            },
            'test': {'service': 'test'},
        }

    def makeService(self):
        with unittest.mock.patch('bugwarrior.config.schema.get_service',
                                 lambda x: DumbService):
            conf = schema.validate_config(self.config, 'general', 'configpath')
        return DumbService(conf['test'], conf['general'])

    def makeIssue(self):
        service = self.makeService()
        return service.get_issue_for_record({})

    def checkArchitecture(self, klass):
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
        with open(services.base.__file__, 'r') as f:
            base = f.read()

        for method in klass.__abstractmethods__:
            references = re.findall(rf'{method}\(', base)
            self.assertEqual(len(references), 1, references)


class TestService(ServiceBase):

    def test_architecture(self):
        self.checkArchitecture(services.base.Service)

    def test_build_annotations_default(self):
        service = self.makeService()

        annotations = service.build_annotations(
            (('some_author', LONG_MESSAGE),), 'example.com')
        self.assertEqual(annotations, [
            '@some_author - Some message that is over 100 characters. Thi...'
        ])

    def test_build_annotations_limited(self):
        self.config['general']['annotation_length'] = '20'
        service = self.makeService()

        annotations = service.build_annotations(
            (('some_author', LONG_MESSAGE),), 'example.com')
        self.assertEqual(
            annotations, ['@some_author - Some message that is...'])

    def test_build_annotations_limitless(self):
        self.config['general']['annotation_length'] = None
        service = self.makeService()

        annotations = service.build_annotations(
            (('some_author', LONG_MESSAGE),), 'example.com')
        self.assertEqual(annotations, [
            f'@some_author - {LONG_MESSAGE}'])


class TestIssue(ServiceBase):

    def test_architecture(self):
        self.checkArchitecture(services.base.Issue)

    def test_build_default_description_default(self):
        issue = self.makeIssue()

        description = issue.build_default_description(LONG_MESSAGE)
        self.assertEqual(
            description, '(bw)Is# - Some message that is over 100 chara')

    def test_build_default_description_limited(self):
        self.config['general']['description_length'] = '20'
        issue = self.makeIssue()

        description = issue.build_default_description(LONG_MESSAGE)
        self.assertEqual(
            description, '(bw)Is# - Some message that is')

    def test_build_default_description_limitless(self):
        self.config['general']['description_length'] = None
        issue = self.makeIssue()

        description = issue.build_default_description(LONG_MESSAGE)
        self.assertEqual(
            description, f'(bw)Is# - {LONG_MESSAGE}')

    def test_get_tags_from_labels_normalization(self):
        self.config['test']['import_labels_as_tags'] = True
        issue = self.makeIssue()

        self.assertEqual(issue.get_tags_from_labels(['needs work']),
                         ['needs_work'])
