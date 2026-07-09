import abc
import pathlib
from pathlib import Path
import re
import unittest.mock

import pytest

from bugwarrior import services
from bugwarrior.config import ServiceConfig

from .base import DumbService, make_issue, make_service

LONG_MESSAGE = """\
Some message that is over 100 characters. This message is so long it's
going to fill up your floppy disk taskwarrior backup. Actually it's not
that long.""".replace('\n', ' ')


def check_architecture(klass: abc.ABCMeta):
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
        assert len(references) == 1, references


class TestService:
    def test_architecture(self):
        check_architecture(services.Service)

    def test_build_annotations_default(self):
        service = make_service()

        annotations = service.build_annotations(
            (('some_author', LONG_MESSAGE),), 'example.com'
        )
        assert annotations == [
            '@some_author - Some message that is over 100 characters. Thi...'
        ]

    def test_build_annotations_limited(self):
        service = make_service(general_overrides={'annotation_length': '20'})

        annotations = service.build_annotations(
            (('some_author', LONG_MESSAGE),), 'example.com'
        )
        assert annotations == ['@some_author - Some message that is...']

    def test_build_annotations_limitless(self):
        service = make_service(general_overrides={'annotation_length': None})

        annotations = service.build_annotations(
            (('some_author', LONG_MESSAGE),), 'example.com'
        )
        assert annotations == [f'@some_author - {LONG_MESSAGE}']

    def test_api_incompatibility_error(self):
        with unittest.mock.patch.object(
            DumbService, 'API_VERSION', new=services.LATEST_API_VERSION + 1
        ):
            with pytest.raises(ValueError, match="Incompatible Service"):
                make_service()

    def test_api_latest_version(self):
        basedir = pathlib.Path(__file__).parent.parent
        with open(basedir / 'bugwarrior/docs/other-services/api.rst', 'r') as f:
            header = f.readline().strip('\n')
            match = re.fullmatch(r'Python API v(?P<version>[0-9]+\.[0-9]+)', header)
            latest_documented = float(match.groupdict()['version'])

        assert latest_documented == services.LATEST_API_VERSION

    def test_api_v1_keyring_service_backwards_compatibility(self):
        class LegacyService:
            API_VERSION = 1.0

            @staticmethod
            def get_keyring_service(config):
                return f'legacy://{config.target}'

        service_config = ServiceConfig(service='legacy', target='legacy-target')
        with unittest.mock.patch(
            'bugwarrior.config.schema.get_service', return_value=LegacyService
        ):
            assert service_config.keyring_service == 'legacy://legacy-target'


class TestIssue:
    def test_architecture(self):
        check_architecture(services.Issue)

    def test_build_default_description_default(self):
        issue = make_issue()

        description = issue.build_default_description(LONG_MESSAGE)
        assert description == '(bw)Is# - Some message that is over 100 chara'

    def test_build_default_description_limited(self):
        issue = make_issue(general_overrides={'description_length': '20'})

        description = issue.build_default_description(LONG_MESSAGE)
        assert description == '(bw)Is# - Some message that is'

    def test_build_default_description_limitless(self):
        issue = make_issue(general_overrides={'description_length': None})

        description = issue.build_default_description(LONG_MESSAGE)
        assert description == f'(bw)Is# - {LONG_MESSAGE}'

    def test_get_tags_from_labels_normalization(self):
        issue = make_issue(config_overrides={'import_labels_as_tags': True})

        assert issue.get_tags_from_labels(['needs work']) == ['needs_work']
