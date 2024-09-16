import itertools
from setuptools import setup, find_packages

with open('VERSION') as version_file:
    version = version_file.read().strip()

with open('bugwarrior/README.rst') as readme_file:
    readme = readme_file.read().strip()
long_description = readme.split('split here', 1)[1]

extras = {
    "activecollab": ["pypandoc", "pyac>=0.1.5"],
    "bts": ["python-debianbts>=2.6.1"],
    "bugzilla": ["python-bugzilla>=2.0.0"],
    "gmail": ["google-api-python-client", "google-auth-oauthlib"],
    "ini2toml": ["ini2toml[full]"],
    "jira": ["jira>=0.22"],
    "kanboard": ["kanboard"],
    "keyring": ["keyring"],
    "phabricator": ["phabricator"],
    "test": [
        "docutils",
        "flake8",
        "pytest",
        "pytest-subtests",
        "responses",
        "sphinx>=1.0",
        "sphinx-click",
        "sphinx-inline-tabs",

        # Workaround https://github.com/python/importlib_metadata/issues/406
        "importlib-metadata<5",
    ],
    "trac": ["offtrac"],
    "versionone": ["v1pysdk"],
}

setup(name='bugwarrior',
      version=version,
      description="Sync github, bitbucket, and trac issues with taskwarrior",
      long_description=long_description,
      classifiers=[
          "Development Status :: 4 - Beta",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: GNU General Public License (GPL)",
          "Programming Language :: Python :: 3",
          "Topic :: Software Development :: Bug Tracking",
          "Topic :: Utilities",
      ],
      keywords='task taskwarrior todo github ',
      author='Ralph Bean',
      author_email='ralph.bean@gmail.com',
      url='http://github.com/ralphbean/bugwarrior',
      license='GPLv3+',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests', 'tests.*']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          "click",
          "dogpile.cache>=0.5.3",
          "jinja2>=2.7.2",
          "lockfile>=0.9.1",
          "pydantic[email]>=2",
          "python-dateutil",
          "pytz",
          "requests",
          "taskw>=0.8",
          # Needed for backwards compatibility with python<=3.10.
          "tomli",
          # Needed for backwards compatibility with python<=3.7.
          "typing-extensions",
      ],
      extras_require={
          'all': list(
              itertools.chain.from_iterable(extras[key] for key in extras)),
          **extras
      },
      entry_points="""
      [console_scripts]
      bugwarrior = bugwarrior:cli
      bugwarrior-pull = bugwarrior:pull
      bugwarrior-vault = bugwarrior:vault
      bugwarrior-uda = bugwarrior:uda
      [bugwarrior.service]
      github=bugwarrior.services.github:GithubService
      gitlab=bugwarrior.services.gitlab:GitlabService
      bitbucket=bugwarrior.services.bitbucket:BitbucketService
      trac=bugwarrior.services.trac:TracService
      bts=bugwarrior.services.bts:BTSService
      bugzilla=bugwarrior.services.bz:BugzillaService
      kanboard=bugwarrior.services.kanboard:KanboardService
      teamlab=bugwarrior.services.teamlab:TeamLabService
      redmine=bugwarrior.services.redmine:RedMineService
      activecollab2=bugwarrior.services.activecollab2:ActiveCollab2Service
      activecollab=bugwarrior.services.activecollab:ActiveCollabService
      jira=bugwarrior.services.jira:JiraService
      phabricator=bugwarrior.services.phab:PhabricatorService
      versionone=bugwarrior.services.versionone:VersionOneService
      pagure=bugwarrior.services.pagure:PagureService
      taiga=bugwarrior.services.taiga:TaigaService
      gerrit=bugwarrior.services.gerrit:GerritService
      trello=bugwarrior.services.trello:TrelloService
      youtrack=bugwarrior.services.youtrack:YoutrackService
      gmail=bugwarrior.services.gmail:GmailService
      teamwork_projects=bugwarrior.services.teamwork_projects:TeamworkService
      pivotaltracker=bugwarrior.services.pivotaltracker:PivotalTrackerService
      azuredevops=bugwarrior.services.azuredevops:AzureDevopsService
      gitbug=bugwarrior.services.gitbug:GitBugService
      deck=bugwarrior.services.deck:NextcloudDeckService
      logseq=bugwarrior.services.logseq:LogseqService
      [ini2toml.processing]
      bugwarrior = bugwarrior.config.ini2toml_plugin:activate
      """,
      )
