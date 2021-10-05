import unittest.mock

import typing_extensions

from bugwarrior import config, services
from bugwarrior.config import load, schema

from .base import ConfigTest

LONG_MESSAGE = """\
Some message that is over 100 characters. This message is so long it's
going to fill up your floppy disk taskwarrior backup. Actually it's not
that long.""".replace('\n', ' ')


class DumbConfig(config.ServiceConfig, prefix='dumb'):
    service: typing_extensions.Literal['test']


class DumbIssue(services.Issue):
    """
    Implement the required methods but they shouldn't be called.
    """
    def get_default_description(self):
        raise NotImplementedError

    def to_taskwarrior(self):
        raise NotImplementedError


class DumbIssueService(services.IssueService):
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
        self.config = load.BugwarriorConfigParser()
        self.config.add_section('general')
        self.config.set('general', 'targets', 'test')
        self.config.set('general', 'interactive', 'false')
        self.config.add_section('test')
        self.config.set('test', 'service', 'test')

    def makeService(self):
        with unittest.mock.patch('bugwarrior.config.schema.get_service',
                                 lambda x: DumbIssueService):
            conf = schema.validate_config(self.config, 'general', 'configpath')
        return DumbIssueService(conf['test'], conf['general'], 'test')

    def makeIssue(self):
        service = self.makeService()
        return service.get_issue_for_record(None)


class TestIssueService(ServiceBase):

    def test_build_annotations_default(self):
        service = self.makeService()

        annotations = service.build_annotations(
            (('some_author', LONG_MESSAGE),), 'example.com')
        self.assertEqual(annotations, [
            u'@some_author - Some message that is over 100 characters. Thi...'
        ])

    def test_build_annotations_limited(self):
        self.config.set('general', 'annotation_length', '20')
        service = self.makeService()

        annotations = service.build_annotations(
            (('some_author', LONG_MESSAGE),), 'example.com')
        self.assertEqual(
            annotations, [u'@some_author - Some message that is...'])

    def test_build_annotations_limitless(self):
        self.config.set('general', 'annotation_length', None)
        service = self.makeService()

        annotations = service.build_annotations(
            (('some_author', LONG_MESSAGE),), 'example.com')
        self.assertEqual(annotations, [
            u'@some_author - {message}'.format(message=LONG_MESSAGE)])


class TestIssue(ServiceBase):

    def test_build_default_description_default(self):
        issue = self.makeIssue()

        description = issue.build_default_description(LONG_MESSAGE)
        self.assertEqual(
            description, u'(bw)Is# - Some message that is over 100 chara')

    def test_build_default_description_limited(self):
        self.config.set('general', 'description_length', '20')
        issue = self.makeIssue()

        description = issue.build_default_description(LONG_MESSAGE)
        self.assertEqual(
            description, u'(bw)Is# - Some message that is')

    def test_build_default_description_limitless(self):
        self.config.set('general', 'description_length', None)
        issue = self.makeIssue()

        description = issue.build_default_description(LONG_MESSAGE)
        self.assertEqual(
            description, u'(bw)Is# - {message}'.format(message=LONG_MESSAGE))
