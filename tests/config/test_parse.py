import unittest

from bugwarrior.config import load, parse


class TestServiceConfig(unittest.TestCase):
    def setUp(self):
        self.target = 'someservice'

        self.config = load.BugwarriorConfigParser()
        self.config.add_section(self.target)
        self.config.set(self.target, 'someprefix.someint', '4')
        self.config.set(self.target, 'someprefix.somenone', '')
        self.config.set(self.target, 'someprefix.somechar', 'somestring')
        self.config.set(self.target, 'someprefix.somebool', 'true')

        self.service_config = parse.ServiceConfig(
            'someprefix', self.config, self.target)

    def test_configparser_proxy(self):
        """
        Methods not defined in ServiceConfig should be proxied to configparser.
        """
        self.assertTrue(
            self.service_config.has_option(self.target, 'someprefix.someint'))

    def test__contains__(self):
        self.assertTrue('someint' in self.service_config)

    def test_get(self):
        self.assertEqual(self.service_config.get('someint'), '4')

    def test_get_default(self):
        self.assertEqual(
            self.service_config.get('someoption', default='somedefault'),
            'somedefault'
        )

    def test_get_default_none(self):
        self.assertIsNone(self.service_config.get('someoption'))

    def test_get_to_type(self):
        self.assertIs(
            self.service_config.get('somebool', to_type=parse.asbool),
            True
        )


class TestCasters(unittest.TestCase):
    def test_asbool(self):
        self.assertEqual(parse.asbool('True'), True)
        self.assertEqual(parse.asbool('False'), False)

    def test_aslist(self):
        self.assertEqual(
            parse.aslist('project_bar,project_baz'),
            ['project_bar', 'project_baz']
        )

    def test_aslist_jinja(self):
        self.assertEqual(
            parse.aslist("work, jira, {{jirastatus|lower|replace(' ','_')}}"),
            ['work', 'jira', "{{jirastatus|lower|replace(' ','_')}}"]
        )

    def test_asint(self):
        self.assertEqual(parse.asint(''), None)
        self.assertEqual(parse.asint('42'), 42)
