import configparser
import itertools
import os
import pathlib
import textwrap
from unittest import TestCase

try:
    import tomllib  # python>=3.11
except ImportError:
    import tomli as tomllib  # backport

from bugwarrior.config import load

from ..base import ConfigTest


class ExampleTest(ConfigTest):
    def setUp(self):
        self.basedir = pathlib.Path(__file__).parent
        super().setUp()

    def test_example_bugwarriorrc(self):
        os.environ['BUGWARRIORRC'] = str(
            self.basedir / 'example-bugwarriorrc')
        load.load_config('general', False, False)

    def test_example_bugwarrior_toml(self):
        os.environ['BUGWARRIORRC'] = str(
            self.basedir / 'example-bugwarrior.toml')
        load.load_config('general', False, False)


class LoadTest(ConfigTest):
    def create(self, path):
        """
        Create an empty file in the temporary directory, return the full path.
        """
        fpath = os.path.join(self.tempdir, path)
        if not os.path.exists(os.path.dirname(fpath)):
            os.makedirs(os.path.dirname(fpath))
        open(fpath, 'a').close()
        return fpath


class TestGetConfigPath(LoadTest):
    def test_path_precedence(self):
        # We're going to manually setup and teardown each subTest.
        self.tearDown()

        config_paths = [  # ordered by precedence
            '.config/bugwarrior/bugwarrior.toml',
            '.config/bugwarrior/bugwarriorrc',
            '.bugwarrior.toml',
            '.bugwarriorrc',
        ]

        # https://docs.python.org/3/library/itertools.html#itertools.combinations
        # > The combination tuples are emitted in lexicographic ordering
        # > according to the order of the input iterable. So, if the input
        # > iterable is sorted, the output tuples will be produced in sorted
        # > order.
        # So as long as the path list is in the correct order, path1 should have
        # precedence.
        for path1, path2 in itertools.combinations(config_paths, 2):
            with self.subTest(path1=path1, path2=path2):
                self.setUp()
                try:
                    config1 = self.create(path1)
                    self.create(path2)
                    self.assertEqual(load.get_config_path(), config1)
                finally:
                    self.tearDown()

    def test_legacy(self):
        """
        Falls back on .bugwarriorrc if it exists
        """
        rc = self.create('.bugwarriorrc')
        self.assertEqual(load.get_config_path(), rc)

    def test_no_file(self):
        """
        If no bugwarriorrc exist anywhere, the path to the prefered one is
        returned.
        """
        self.assertEqual(
            load.get_config_path(),
            os.path.join(self.tempdir, '.config/bugwarrior/bugwarrior.toml'))

    def test_BUGWARRIORRC(self):
        """
        If $BUGWARRIORRC is set, it takes precedence over everything else (even
        if the file doesn't exist).
        """
        rc = os.path.join(self.tempdir, 'my-bugwarriorc')
        os.environ['BUGWARRIORRC'] = rc
        self.create('.bugwarriorrc')
        self.create('.config/bugwarrior/bugwarriorrc')
        self.assertEqual(load.get_config_path(), rc)

    def test_BUGWARRIORRC_empty(self):
        """
        If $BUGWARRIORRC is set but empty, it is not used and the default file
        is used instead.
        """
        os.environ['BUGWARRIORRC'] = ''
        rc = self.create('.config/bugwarrior/bugwarriorrc')
        self.assertEqual(load.get_config_path(), rc)


class TestParseFile(LoadTest):
    def test_toml(self):
        config_path = self.create('.bugwarrior.toml')
        with open(config_path, 'w') as fout:
            fout.write(textwrap.dedent("""
                [general]
                foo = "bar"
            """))

        load.parse_file(config_path)

    def test_toml_invalid(self):
        config_path = self.create('.bugwarrior.toml')
        with open(config_path, 'w') as fout:
            fout.write(textwrap.dedent("""
                [general
                foo = "bar"
            """))

        with self.assertRaises(tomllib.TOMLDecodeError):
            load.parse_file(config_path)

    def test_ini(self):
        config_path = self.create('.bugwarriorrc')
        with open(config_path, 'w') as fout:
            fout.write(textwrap.dedent("""
                [general]
                foo = bar
            """))
        config = load.parse_file(config_path)

        self.assertEqual(config, {'general': {'foo': 'bar'}})

    def test_ini_invalid(self):
        config_path = self.create('.bugwarriorrc')
        with open(config_path, 'w') as fout:
            fout.write(textwrap.dedent("""
                [general
                foo = bar
            """))

        with self.assertRaises(configparser.MissingSectionHeaderError):
            load.parse_file(config_path)

    def test_ini_options_renamed(self):
        """
        Prefixes are removed and log.* are renamed log_* in main section.
        """

        config_path = self.create('.bugwarriorrc')
        with open(config_path, 'w') as fout:
            fout.write(textwrap.dedent("""
                [general]
                foo = bar
                log.level = DEBUG
                [github]
                service = github
                github.optionname = something
            """))
        config = load.parse_file(config_path)

        self.assertIn('optionname', config['github'])
        self.assertNotIn('prefix.optionname', config['github'])

        self.assertIn('log_level', config['general'])
        self.assertNotIn('log.level', config['general'])


class TestConfig(TestCase):
    def test_getitem(self):
        config = load.Config(foo='bar')
        self.assertEqual(config['foo'], 'bar')

    def test_getitem_nested(self):
        config = load.Config(foo={'bar': {'baz': 'qux'}})
        self.assertEqual(config['foo.bar.baz'], 'qux')
