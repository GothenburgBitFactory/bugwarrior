import configparser
import itertools
from pathlib import Path
import textwrap
import tomllib

import pytest

from bugwarrior.config import load


@pytest.fixture
def create_filepath(tmp_path):
    """
    Return a factory creating an empty file in the temporary home directory.
    """

    def create_filepath(path):
        fpath = tmp_path / path
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.touch()
        return str(fpath)

    return create_filepath


class TestExample:
    @pytest.mark.parametrize(
        'rcfile', ['example-bugwarriorrc', 'example-bugwarrior.toml']
    )
    def test_example(self, rcfile, monkeypatch):
        monkeypatch.setenv('BUGWARRIORRC', str(Path(__file__).parent / rcfile))
        load.load_config('general', False)


#: Candidate bugwarriorrc locations, ordered by precedence.
CONFIG_PATHS = [
    '.config/bugwarrior/bugwarriorrc',
    '.config/bugwarrior/bugwarrior.toml',
    '.bugwarriorrc',
    '.bugwarrior.toml',
]


class TestGetConfigPath:
    # https://docs.python.org/3/library/itertools.html#itertools.combinations
    # > The combination tuples are emitted in lexicographic ordering
    # > according to the order of the input iterable. So, if the input
    # > iterable is sorted, the output tuples will be produced in sorted
    # > order.
    # So as long as the path list is in the correct order, path1 should have
    # precedence.
    @pytest.mark.parametrize(
        ('path1', 'path2'), list(itertools.combinations(CONFIG_PATHS, 2))
    )
    def test_path_precedence(self, path1, path2, create_filepath):
        config1 = create_filepath(path1)
        create_filepath(path2)
        assert load.get_config_path() == config1

    def test_legacy(self, create_filepath):
        """
        Falls back on .bugwarriorrc if it exists
        """
        rc = create_filepath('.bugwarriorrc')
        assert load.get_config_path() == rc

    def test_no_file(self, tmp_path):
        """
        If no bugwarriorrc exist anywhere, the path to the prefered one is
        returned.
        """
        assert load.get_config_path() == str(
            tmp_path / '.config/bugwarrior/bugwarriorrc'
        )

    def test_BUGWARRIORRC(self, create_filepath, tmp_path, monkeypatch):
        """
        If $BUGWARRIORRC is set, it takes precedence over everything else (even
        if the file doesn't exist).
        """
        rc = str(tmp_path / 'my-bugwarriorc')
        monkeypatch.setenv('BUGWARRIORRC', rc)
        create_filepath('.bugwarriorrc')
        create_filepath('.config/bugwarrior/bugwarriorrc')
        assert load.get_config_path() == rc

    def test_BUGWARRIORRC_empty(self, create_filepath, monkeypatch):
        """
        If $BUGWARRIORRC is set but empty, it is not used and the default file
        is used instead.
        """
        monkeypatch.setenv('BUGWARRIORRC', '')
        rc = create_filepath('.config/bugwarrior/bugwarriorrc')
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
        with pytest.raises(
            ValueError, match='general.somechar must be an integer or empty.'
        ):
            config.getint('general', 'somechar')


class TestParseFile:
    def test_toml(self, create_filepath):
        config_path = create_filepath('.bugwarrior.toml')
        with open(config_path, 'w') as fout:
            fout.write(
                textwrap.dedent("""
                [general]
                foo = "bar"
            """)
            )

        load.parse_file(config_path)

    def test_ini(self, create_filepath):
        config_path = create_filepath('.bugwarriorrc')
        with open(config_path, 'w') as fout:
            fout.write(
                textwrap.dedent("""
                [general]
                foo = bar
            """)
            )
        config = load.parse_file(config_path)

        assert config == {'flavor': {'general': {'foo': 'bar'}}, 'services': []}

    def test_toml_invalid(self, create_filepath):
        config_path = create_filepath('.bugwarrior.toml')
        with open(config_path, 'w') as fout:
            fout.write(
                textwrap.dedent("""
                [general
                foo = "bar"
            """)
            )

        with pytest.raises(tomllib.TOMLDecodeError):
            load.parse_file(config_path)

    def test_ini_invalid(self, create_filepath):
        config_path = create_filepath('.bugwarriorrc')
        with open(config_path, 'w') as fout:
            fout.write(
                textwrap.dedent("""
                [general
                foo = bar
            """)
            )

        with pytest.raises(configparser.MissingSectionHeaderError):
            load.parse_file(config_path)

    def test_toml_flavors(self, create_filepath):
        config_path = create_filepath('.bugwarrior.toml')

        with open(config_path, 'w') as fout:
            fout.write('[flavor.myflavor]\ntargets = ["my_gitlab"]')
        config = load.parse_file(config_path)
        assert config == {
            'flavor': {'myflavor': {'targets': ['my_gitlab']}},
            'services': [],
        }

    def test_ini_flavors(self, create_filepath):
        config_path = create_filepath('.bugwarriorrc')
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

    def test_ini_options_renamed(self, create_filepath):
        """
        Prefixes are removed and log.* are renamed log_* in main section.
        """

        config_path = create_filepath('.bugwarriorrc')
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

    def test_ini_missing_prefix(self, create_filepath):
        config_path = create_filepath('.bugwarriorrc')
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

    def test_ini_wrong_prefix(self, create_filepath):
        config_path = create_filepath('.bugwarriorrc')
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


class TestLoadConfig:
    def test_main_section_does_not_exist(self, create_filepath, caplog):
        config_path = create_filepath(".bugwarriorrc")
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

        assert len(caplog.records) == 1
        assert "No section: 'general'" in caplog.records[0].message
