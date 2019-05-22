# -*- coding: utf-8 -*-

import unittest
from six.moves import configparser

import taskw.task
from bugwarrior import db

from .base import ConfigTest


class TestMergeLeft(unittest.TestCase):
    def setUp(self):
        self.issue_dict = {'annotations': ['testing']}

    def assertMerged(self, local, remote, **kwargs):
        db.merge_left('annotations', local, remote, **kwargs)
        self.assertEqual(local, remote)

    def test_with_dict(self):
        self.assertMerged({}, self.issue_dict)

    def test_with_taskw(self):
        self.assertMerged(taskw.task.Task({}), self.issue_dict)

    def test_already_in_sync(self):
        self.assertMerged(self.issue_dict, self.issue_dict)

    def test_rough_equality_hamming_false(self):
        """ When hamming=False, rough equivalents are duplicated. """
        remote = {'annotations': ['\n  testing  \n']}

        db.merge_left('annotations', self.issue_dict, remote, hamming=False)
        self.assertEqual(len(self.issue_dict['annotations']), 2)

    def test_rough_equality_hamming_true(self):
        """ When hamming=True, rough equivalents are not duplicated. """
        remote = {'annotations': ['\n  testing  \n']}

        db.merge_left('annotations', self.issue_dict, remote, hamming=True)
        self.assertEqual(len(self.issue_dict['annotations']), 1)


class TestSynchronize(ConfigTest):

    def test_synchronize(self):

        def get_tasks(tw):
            tasks = tw.load_tasks()

            # Remove non-deterministic keys.
            del tasks['pending'][0]['modified']
            del tasks['pending'][0]['entry']
            del tasks['pending'][0]['uuid']

            return tasks

        config = configparser.RawConfigParser()
        config.add_section('general')
        config.set('general', 'targets', 'my_service')
        config.set('general', 'static_fields', 'project, priority')
        config.add_section('my_service')
        config.set('my_service', 'service', 'github')

        tw = taskw.TaskWarrior(self.taskrc)
        self.assertEqual(tw.load_tasks(), {'completed': [], 'pending': []})

        issue = {
            'description': 'Blah blah blah. ☃',
            'project': 'sample_project',
            'githubtype': 'issue',
            'githuburl': 'https://example.com',
            'priority': 'M',
        }

        # TEST NEW ISSUE AND EXISTING ISSUE.
        for _ in range(2):
            # Use an issue generator with two copies of the same issue.
            # These should be de-duplicated in db.synchronize before
            # writing out to taskwarrior.
            # https://github.com/ralphbean/bugwarrior/issues/601
            issue_generator = iter((issue, issue,))
            db.synchronize(issue_generator, config, 'general')

            self.assertEqual(get_tasks(tw), {
                'completed': [],
                'pending': [{
                    u'project': u'sample_project',
                    u'priority': u'M',
                    u'status': u'pending',
                    u'description': u'Blah blah blah. ☃',
                    u'githuburl': u'https://example.com',
                    u'githubtype': u'issue',
                    u'id': 1,
                    u'urgency': 4.9,
                }]})

        # TEST CHANGED ISSUE.
        issue['description'] = 'Yada yada yada.'

        # Change static field
        issue['project'] = 'other_project'

        db.synchronize(iter((issue,)), config, 'general')

        self.assertEqual(get_tasks(tw), {
            'completed': [],
            'pending': [{
                u'priority': u'M',
                u'project': u'sample_project',
                u'status': u'pending',
                u'description': u'Yada yada yada.',
                u'githuburl': u'https://example.com',
                u'githubtype': u'issue',
                u'id': 1,
                u'urgency': 4.9,
            }]})

        # TEST CLOSED ISSUE.
        db.synchronize(iter(()), config, 'general')

        tasks = tw.load_tasks()

        # Remove non-deterministic keys.
        del tasks['completed'][0]['modified']
        del tasks['completed'][0]['entry']
        del tasks['completed'][0]['end']
        del tasks['completed'][0]['uuid']

        self.assertEqual(tasks, {
            'completed': [{
                u'project': u'sample_project',
                u'description': u'Yada yada yada.',
                u'githubtype': u'issue',
                u'githuburl': u'https://example.com',
                u'id': 0,
                u'priority': u'M',
                u'status': u'completed',
                u'urgency': 4.9,
            }],
             'pending': []})

class TestUDAs(ConfigTest):
    def test_udas(self):
        config = configparser.RawConfigParser()
        config.add_section('general')
        config.set('general', 'targets', 'my_service')
        config.add_section('my_service')
        config.set('my_service', 'service', 'github')

        udas = sorted(list(db.get_defined_udas_as_strings(config, 'general')))
        self.assertEqual(udas, [
            u'uda.githubbody.label=Github Body',
            u'uda.githubbody.type=string',
            u'uda.githubclosedon.label=GitHub Closed',
            u'uda.githubclosedon.type=date',
            u'uda.githubcreatedon.label=Github Created',
            u'uda.githubcreatedon.type=date',
            u'uda.githubmilestone.label=Github Milestone',
            u'uda.githubmilestone.type=string',
            u'uda.githubnamespace.label=Github Namespace',
            u'uda.githubnamespace.type=string',
            u'uda.githubnumber.label=Github Issue/PR #',
            u'uda.githubnumber.type=numeric',
            u'uda.githubrepo.label=Github Repo Slug',
            u'uda.githubrepo.type=string',
            u'uda.githubstate.label=GitHub State',
            u'uda.githubstate.type=string',
            u'uda.githubtitle.label=Github Title',
            u'uda.githubtitle.type=string',
            u'uda.githubtype.label=Github Type',
            u'uda.githubtype.type=string',
            u'uda.githubupdatedat.label=Github Updated',
            u'uda.githubupdatedat.type=date',
            u'uda.githuburl.label=Github URL',
            u'uda.githuburl.type=string',
            u'uda.githubuser.label=Github User',
            u'uda.githubuser.type=string',
        ])
