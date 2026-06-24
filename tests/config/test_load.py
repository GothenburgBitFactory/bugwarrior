import configparser
import itertools
import os
from pathlib import Path
import textwrap
import tomllib

import pytest

from bugwarrior.config import load

from ..base import ConfigTest


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


class ExampleTest(ConfigTest):
    def setUp(self):
        self.basedir = Path(__file__).parent
        super().setUp()

    def test_example(self):
        for rcfile in ('example-bugwarriorrc', 'example-bugwarrior.toml'):
            with self.subTest(rcfile=rcfile):
                os.environ['BUGWARRIORRC'] = str(self.basedir / rcfile)
                load.load_config('general', False)


class TestGetConfigPath(LoadTest):
    def test_path_precedence(self):
        # We're going to manually setup and teardown each subTest.
        self.tearDown()

        config_paths = [  # ordered by precedence
            '.config/bugwarrior/bugwarriorrc',
            '.config/bugwarrior/bugwarrior.toml',
            '.bugwarriorrc',
            '.bugwarrior.toml',
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
                    assert load.get_config_path() == config1
                finally:
                    self.tearDown()

    def test_legacy(self):
        """
        Falls back on .bugwarriorrc if it exists
        """
        rc = self.create('.bugwarriorrc')
        assert load.get_config_path() == rc

    def test_no_file(self):
        """
        If no bugwarriorrc exist anywhere, the path to the prefered one is
        returned.
        """
        assert load.get_config_path() == os.path.join(
            self.tempdir, '.config/bugwarrior/bugwarriorrc'
        )

    def test_BUGWARRIORRC(self):
        """
        If $BUGWARRIORRC is set, it takes precedence over everything else (even
        if the file doesn't exist).
        """
        rc = os.path.join(self.tempdir, 'my-bugwarriorc')
        os.environ['BUGWARRIORRC'] = rc
        self.create('.bugwarriorrc')
        self.create('.config/bugwarrior/bugwarriorrc')
        assert load.get_config_path() == rc

    def test_BUGWARRIORRC_empty(self):
        """
        If $BUGWARRIORRC is set but empty, it is not used and the default file
        is used instead.
        """
        os.environ['BUGWARRIORRC'] = ''
        rc = self.create('.config/bugwarrior/bugwarriorrc')
        assert load.get_config_path() == rc


class TestBugwarriorConfigParser:
    @pytest.fixture
    def config(self):
        config = load.BugwarriorConfigParser()
        config['general'] = {'someint': '4', 'somenone': '', 'somechar': 'somestring'}
        return config

    def test_getint(self, config):
        assert config.getint('general', 'someint') == 4

    def test_getint_none(self, config):
        assert config.getint('general', 'somenone') is None

    def test_getint_valueerror(self, config):
        with pytest.raises(ValueError):
            config.getint('general', 'somechar')


class TestParseFile(LoadTest):
    def test_toml(self):
        config_path = self.create('.bugwarrior.toml')
        with open(config_path, 'w') as fout:
            fout.write(
                textwrap.dedent("""
                [general]
                foo = "bar"
            """)
            )

        load.parse_file(config_path)

    def test_ini(self):
        config_path = self.create('.bugwarriorrc')
        with open(config_path, 'w') as fout:
            fout.write(
                textwrap.dedent("""
                [general]
                foo = bar
            """)
            )
        config = load.parse_file(config_path)

        assert config == {'flavor': {'general': {'foo': 'bar'}}, 'services': []}

    def test_toml_invalid(self):
        config_path = self.create('.bugwarrior.toml')
        with open(config_path, 'w') as fout:
            fout.write(
                textwrap.dedent("""
                [general
                foo = "bar"
            """)
            )

        with pytest.raises(tomllib.TOMLDecodeError):
            load.parse_file(config_path)

    def test_ini_invalid(self):
        config_path = self.create('.bugwarriorrc')
        with open(config_path, 'w') as fout:
            fout.write(
                textwrap.dedent("""
                [general
                foo = bar
            """)
            )

        with pytest.raises(configparser.MissingSectionHeaderError):
            load.parse_file(config_path)

    def test_toml_flavors(self):
        config_path = self.create('.bugwarrior.toml')

        with open(config_path, 'w') as fout:
            fout.write('[flavor.myflavor]\ntargets = ["my_gitlab"]')
        config = load.parse_file(config_path)
        assert config == {
            'flavor': {'myflavor': {'targets': ['my_gitlab']}},
            'services': [],
        }

    def test_ini_flavors(self):
        config_path = self.create('.bugwarriorrc')
        with open(config_path, 'w') as fout:
            fout.write(
                textwrap.dedent("""
                [flavor.myflavor]
                targets = my_gitlab
            """)
            )
        config = load.parse_file(config_path)

        assert config == {
            'flavor': {'myflavor': {'targets': 'my_gitlab'}},
            'services': [],
        }

    def test_ini_options_renamed(self):
        """
        Prefixes are removed and log.* are renamed log_* in main section.
        """

        config_path = self.create('.bugwarriorrc')
        with open(config_path, 'w') as fout:
            fout.write(
                textwrap.dedent("""
                [general]
                foo = bar
                log.level = DEBUG
                [baz]
                service = qux
                qux.optionname
            """)
            )
        config = load.parse_file(config_path)

        baz_service = next(svc for svc in config['services'] if svc['target'] == 'baz')
        assert 'optionname' in baz_service
        assert 'prefix.optionname' not in baz_service

        assert 'log_level' in config['flavor']['general']
        assert 'log.level' not in config['flavor']['general']

    def test_ini_missing_prefix(self):
        config_path = self.create('.bugwarriorrc')
        with open(config_path, 'w') as fout:
            fout.write(
                textwrap.dedent("""
                [general]
                foo = bar
                [baz]
                service = qux
                optionname
            """)
            )

        with pytest.raises(SystemExit):
            load.parse_file(config_path)

    def test_ini_wrong_prefix(self):
        config_path = self.create('.bugwarriorrc')
        with open(config_path, 'w') as fout:
            fout.write(
                textwrap.dedent("""
                [general]
                foo = bar
                [baz]
                service = qux
                wrong.optionname
            """)
            )

        with pytest.raises(SystemExit):
            load.parse_file(config_path)


class TestLoadConfig(LoadTest):
    def setUp(self):
        self.basedir = Path(__file__).parent
        super().setUp()

    def test_main_section_does_not_exist(self):
        config_path = self.create(".bugwarriorrc")
        with open(config_path, 'w') as fout:
            fout.write(
                textwrap.dedent("""
                [redmine]
                service = redmine
                redmine.url = example.com
            """)
            )

        with pytest.raises(SystemExit):
            load.load_config("general", False)

        assert len(self.caplog.records) == 1
        assert "No section: 'general'" in self.caplog.records[0].message
