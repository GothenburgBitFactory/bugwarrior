import copy
from types import SimpleNamespace

import pytest
import taskw.task

from bugwarrior import db
from bugwarrior.collect import CollectedIssue
from bugwarrior.config import schema
from bugwarrior.config.validation import Config

from .base import DumbConfig, register_services


class TestMergeAnnotations:
    def test_merges_local_and_remote_annotations(self):
        local = {'annotations': ['existing']}
        remote = {'annotations': ['new', 'new']}

        assert db.merge_annotations(local, remote) == ['existing', 'new', 'new']

    def test_skips_normalized_matches(self):
        local = {'annotations': ['testing']}
        remote = {'annotations': ['\n  testing  \n']}

        assert db.merge_annotations(local, remote) == ['testing']

    def test_adds_annotation_that_extends_existing_one(self):
        local = {'annotations': ['testing']}
        remote = {'annotations': ['testing with more detail']}

        assert db.merge_annotations(local, remote) == [
            'testing',
            'testing with more detail',
        ]

    def test_handles_missing_annotations(self):
        assert db.merge_annotations({}, {}) == []
        assert db.merge_annotations({}, {'annotations': ['new']}) == ['new']


class TestMergeTags:
    def test_merges_and_sorts_unique_tags(self):
        main_conf = SimpleNamespace(replace_tags=False, static_tags=[])
        local = {'tags': ['existing', 'shared']}
        remote = {'tags': ['new', 'shared']}

        assert db.merge_tags(main_conf, local, remote) == ['existing', 'new', 'shared']

    def test_replaces_non_static_local_tags_when_configured(self):
        main_conf = SimpleNamespace(replace_tags=True, static_tags=['keep'])
        local = {'tags': ['drop', 'keep']}
        remote = {'tags': ['new']}

        assert db.merge_tags(main_conf, local, remote) == ['keep', 'new']

    def test_handles_missing_tags(self):
        main_conf = SimpleNamespace(replace_tags=False, static_tags=[])

        assert db.merge_tags(main_conf, {}, {}) == []
        assert db.merge_tags(main_conf, {}, {'tags': ['new']}) == ['new']


class TestSynchronize:
    @pytest.fixture(autouse=True)
    def registered_services(self):
        with register_services():
            yield

    @pytest.fixture
    def bwconfig(self, config_environment):
        return Config(
            service_configs=[DumbConfig(target='my_service')],
            main=schema.MainSectionConfig(
                targets=['my_service'],
                taskrc=config_environment.taskrc,
                static_fields=['project', 'priority'],
            ),
        )

    @pytest.fixture
    def tw(self, config_environment):
        return taskw.TaskWarrior(config_environment.taskrc)

    def synchronize(self, bwconfig, issues_data):

        issue_generator = [
            CollectedIssue(
                task_data=copy.deepcopy(issue_data),
                target="my_service",
                identifier="abcd",
            )
            for issue_data in issues_data
        ]
        db.synchronize(iter(issue_generator), bwconfig)

    def remove_non_deterministic_keys(self, tasks):
        for status in ['pending', 'completed']:
            for task in tasks[status]:
                del task['modified']
                del task['entry']
                del task['uuid']
                task['tags'] = sorted(task['tags'])

        return tasks

    def get_tasks(self, tw):

        return self.remove_non_deterministic_keys(tw.load_tasks())

    def test_synchronize(self, bwconfig, tw):

        assert tw.load_tasks() == {'completed': [], 'pending': []}

        issue = {
            'description': 'Blah blah blah. ☃',
            'project': 'sample_project',
            'dumbtype': 'issue',
            'dumburl': 'https://example.com',
            'priority': 'M',
            'tags': ['foo'],
        }
        duplicate_issue = copy.deepcopy(issue)
        duplicate_issue['tags'] = ['bar']

        # TEST NEW ISSUE AND EXISTING ISSUE.
        for _ in range(2):
            # Use an issue generator with two copies of the same issue.
            # These should be de-duplicated in db.synchronize before
            # writing out to taskwarrior.
            # https://github.com/ralphbean/bugwarrior/issues/601
            self.synchronize(bwconfig, [issue, duplicate_issue])

            assert self.get_tasks(tw) == {
                'completed': [],
                'pending': [
                    {
                        'project': 'sample_project',
                        'priority': 'M',
                        'status': 'pending',
                        'description': 'Blah blah blah. ☃',
                        'dumburl': 'https://example.com',
                        'dumbtype': 'issue',
                        'id': 1,
                        'tags': ['bar', 'foo'],
                        'urgency': 5.8,
                    }
                ],
            }

        # TEST CHANGED ISSUE.
        issue['description'] = 'Yada yada yada.'

        # Change static field
        issue['project'] = 'other_project'
        self.synchronize(bwconfig, [issue])

        assert self.get_tasks(tw) == {
            'completed': [],
            'pending': [
                {
                    'priority': 'M',
                    'project': 'sample_project',
                    'status': 'pending',
                    'description': 'Yada yada yada.',
                    'dumburl': 'https://example.com',
                    'dumbtype': 'issue',
                    'id': 1,
                    'tags': ['bar', 'foo'],
                    'urgency': 5.8,
                }
            ],
        }

        # TEST CLOSED ISSUE.
        self.synchronize(bwconfig, [])

        completed_tasks = tw.load_tasks()

        tasks = self.remove_non_deterministic_keys(copy.deepcopy(completed_tasks))
        del tasks['completed'][0]['end']
        assert tasks == {
            'completed': [
                {
                    'project': 'sample_project',
                    'description': 'Yada yada yada.',
                    'dumbtype': 'issue',
                    'dumburl': 'https://example.com',
                    'id': 0,
                    'priority': 'M',
                    'status': 'completed',
                    'tags': ['bar', 'foo'],
                    'urgency': 5.8,
                }
            ],
            'pending': [],
        }

        # TEST REOPENED ISSUE
        self.synchronize(bwconfig, [issue])

        tasks = tw.load_tasks()
        assert completed_tasks['completed'][0]['uuid'] == tasks['pending'][0]['uuid']

        tasks = self.remove_non_deterministic_keys(tasks)
        assert tasks == {
            'completed': [],
            'pending': [
                {
                    'priority': 'M',
                    'project': 'sample_project',
                    'status': 'pending',
                    'description': 'Yada yada yada.',
                    'dumburl': 'https://example.com',
                    'dumbtype': 'issue',
                    'id': 1,
                    'tags': ['bar', 'foo'],
                    'urgency': 5.8,
                }
            ],
        }


class TestUDAs:
    def test_udas(self, config_environment):
        with register_services():
            conf = Config(
                service_configs=[DumbConfig(target='my_service')],
                main=schema.MainSectionConfig(
                    targets=['my_service'], taskrc=config_environment.taskrc
                ),
            )
            udas = sorted(db.get_defined_udas_as_strings(conf))
        assert udas == [
            'uda.dumbtype.label=Dumb Type',
            'uda.dumbtype.type=string',
            'uda.dumburl.label=Dumb URL',
            'uda.dumburl.type=string',
        ]
