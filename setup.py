from setuptools import setup, find_packages

version = '1.7.0'

f = open('bugwarrior/README.rst')
long_description = f.read().strip()
long_description = long_description.split('split here', 1)[1]
f.close()

setup(name='bugwarrior',
      version=version,
      description="Sync github, bitbucket, and trac issues with taskwarrior",
      long_description=long_description,
      classifiers=[
          "Development Status :: 4 - Beta",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: GNU General Public License (GPL)",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 3",
          "Topic :: Software Development :: Bug Tracking",
          "Topic :: Utilities",
      ],
      keywords='task taskwarrior todo github ',
      author='Ralph Bean',
      author_email='ralph.bean@gmail.com',
      url='http://github.com/ralphbean/bugwarrior',
      license='GPLv3+',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          "requests",
          "taskw >= 0.8",
          "python-dateutil",
          "pytz",
          "six>=1.9.0",
          "jinja2>=2.7.2",
          "dogpile.cache>=0.5.3",
          "lockfile>=0.9.1",
          "click",
          "future",
      ],
      extras_require=dict(
          keyring=["keyring"],
          jira=["jira>=0.22"],
          megaplan=["megaplan>=1.4"],
          activecollab=["pypandoc", "pyac>=0.1.5"],
          bts=["PySimpleSOAP", "python-debianbts>=2.6.1"],
          trac=["offtrac"],
          bugzilla=["python-bugzilla"],
          gmail=["google-api-python-client", "oauth2client<4.0.0"],
      ),
      tests_require=[
          "Mock",
          "nose",
          "responses",
          "bugwarrior[jira]",
          "bugwarrior[megaplan]",
          "bugwarrior[activecollab]",
          "bugwarrior[bts]",
          "bugwarrior[gmail]",
          "bugwarrior[trac]",
          "bugwarrior[bugzilla]",
      ],
      test_suite='nose.collector',
      entry_points="""
      [console_scripts]
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
      teamlab=bugwarrior.services.teamlab:TeamLabService
      redmine=bugwarrior.services.redmine:RedMineService
      activecollab2=bugwarrior.services.activecollab2:ActiveCollab2Service
      activecollab=bugwarrior.services.activecollab:ActiveCollabService
      jira=bugwarrior.services.jira:JiraService
      megaplan=bugwarrior.services.megaplan:MegaplanService
      phabricator=bugwarrior.services.phab:PhabricatorService
      versionone=bugwarrior.services.versionone:VersionOneService
      pagure=bugwarrior.services.pagure:PagureService
      taiga=bugwarrior.services.taiga:TaigaService
      gerrit=bugwarrior.services.gerrit:GerritService
      trello=bugwarrior.services.trello:TrelloService
      youtrack=bugwarrior.services.youtrack:YoutrackService
      gmail=bugwarrior.services.gmail:GmailService
      teamworks_projects=bugwarrior.services.teamworks_projects:TeamworksService
      """,
      )
