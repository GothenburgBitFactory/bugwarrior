bugwarrior - Pull tickets from github, bitbucket, bugzilla, jira, trac, and others into taskwarrior
===================================================================================================

.. split here

``bugwarrior`` is a command line utility for updating your local `taskwarrior <http://taskwarrior.org>`_ database from your forge issue trackers.

It currently supports the following remote resources:

 - `github <http://github.com>`_ (api v3)
 - `bitbucket <http://bitbucket.org>`_
 - `trac <http://trac.edgewall.org/>`_
 - `bugzilla <http://www.bugzilla.org/>`_
 - `megaplan <http://www.megaplan.ru/>`_
 - `teamlab <http://www.teamlab.com/>`_
 - `redmine <http://www.redmine.org/>`_
 - `jira <http://www.atlassian.com/software/jira/overview>`_
 - `activecollab <http://www.activecollab.com>`_ (2.x and 3.x)

Configuring
-----------

Create a ``~/.bugwarriorrc`` file with the following contents.

.. example

::

  # Example ~/.bugwarriorrc
  #
  # PASSWORD LOOKUP STRATEGIES:
  # Use "password = @oracle:use_keyring" to retrieve a password from a keyring.
  # Use "password = @oracle:ask_password" to ask the user for the password.
  # Use "password = @oracle:eval:<command>" to use the output of <command> as the password.
  # Note that using one of these strategies is in general more secure
  # than storing a password in plain text.

  # General stuff.
  [general]
  # Here you define a comma separated list of targets.  Each of them must have a
  # section below determining their properties, how to query them, etc.  The name
  # is just a symbol, and doesn't have any functional importance.
  targets = my_github, my_bitbucket, paj_bitbucket, moksha_trac, bz.redhat

  # If unspecified, the default taskwarrior config will be used.
  #taskrc = /path/to/.taskrc

  # Defines whether or not issues should be matched based upon their description.
  # For historical reasons, and by default, we will attempt to match issues
  # based upon the presence of the '(bw)' marker in the task description.
  # If this is false, we will only select issues having the appropriate UDA
  # fields defined
  #legacy_matching=False

  # log.level specifices the verbosity.  The default is DEBUG.
  # log.level can be one of DEBUG, INFO, WARNING, ERROR, CRITICAL, DISABLED
  #log.level = DEBUG

  # If log.file is specified, output will be redirected there.  If it remains
  # unspecified, output is sent to sys.stderr
  #log.file = /var/log/bugwarrior.log

  # This is an experimental mode where bugwarrior will query all of your
  # online sources simultaneously.  It works as far as I've tested it, so
  # give it a try.  Please backup your ~/.task/ directory first and report
  # any problems if you encounter them at
  # https://github.com/ralphbean/bugwarrior/issues
  #multiprocessing = False

  # Configure the default description or annotation length.
  #annotation_length = 45
  #description_length = 35

  # This section is for configuring notifications when bugwarrior-pull runs,
  # and when issues are created, updated, or deleted by bugwarrior-pull.
  # Three backend are currently suported:
  #
  #  - growlnotify (v2)   Mac OS X   "gntp" must be installed
  #  - gobject            Linux      python gobject must be installed
  #  - pynotify           Linux      "pynotify" must be installed
  #
  # To configure, adjust the settings below.  Note that neither of the
  # "sticky" options have any effect on Linux with pynotify.  They only work
  # for growlnotify.
  [notifications]
  # notifications = True
  # backend = growlnotify
  # finished_querying_sticky = False
  # task_crud_sticky = True


  # This is a github example.  It says, "scrape every issue from every repository
  # on http://github.com/ralphbean.  It doesn't matter if ralphbean owns the issue
  # or not."
  [my_github]
  service = github
  github.username = ralphbean
  default_priority = H

  # You can override how an issue's description is created by entering
  # a one-line Jinja template like the below; in addition to the default
  # taskwarrior issue properties (project, priority, due, etc), the
  # following properties are available for Github issues:
  # - github_title: The title of the issue in Github
  # - github_url: This issue or pull request's URL.
  # - github_pr: The pull request # of the pull request in Github.
  # - github_issue: The issue # of this issue in Github.
  # - github_type: The type of github entry this is ('pull_request' or 'issue')
  #description_template = {% if type == 'pull_request' %}PR #{{ github_pr }}{% else %}Issue #{{ github_issue }}{% endif %}: {{ github_title }}

  # I want taskwarrior to include issues from all my repos, except these
  # two because they're spammy or something.
  github.exclude_repos = project_bar,project_baz

  # Working with a large number of projects, instead of excluding most of them I
  # can also simply include just a limited set.
  github.include_repos = project_foo,project_foz

  # Note that login and username can be different.  I can login as me, but
  # scrape issues from an organization's repos.
  github.login = ralphbean
  github.password = OMG_LULZ

  # This is the same thing, but for bitbucket.  Each target entry must have a
  # 'service' attribute which must be one of the supported services (like
  # 'github', 'bitbucket', 'trac', etc...).
  [my_bitbucket]
  service = bitbucket
  bitbucket.username = ralphbean
  bitbucket.password = mypassword
  default_priority = M

  # You can override how an issue's description is created by entering
  # a one-line Jinja template like the below; in addition to the default
  # taskwarrior issue properties (project, priority, due, etc), the
  # following properties are available for Bitbucket issues:
  # - bitbucket_title
  # - bitbucket_url
  # - bitbucket_id
  #description_template = #{{ bitbucket_id }}: {{ bitbucket_title }}

  # Here's another bitbucket one.  Here we want to scrape the issues from repos of
  # another user, but only include them in the taskwarrior db if they're assigned
  # to me.
  [paj_bitbucket]
  service = bitbucket
  bitbucket.username = paj
  bitbucket.only_if_assigned = ralphbean
  default_priority = L

  # Here's an example of a trac target.  Scrape every ticket and only include them
  # if 1) they're owned by me or 2) they're currently unassigned.
  # Note -- You must have the trac XML-RPC plugin installed and configured to work
  # over HTTP.
  [moksha_trac]
  service = trac

  trac.base_uri = fedorahosted.org/moksha
  trac.username = ralph
  trac.password = OMG_LULZ

  only_if_assigned = ralph
  also_unassigned = True
  default_priority = H

  # You can override how an issue's description is created by entering
  # a one-line Jinja template like the below; in addition to the default
  # taskwarrior issue properties (project, priority, due, etc), the
  # following properties are available for Trac issues:
  # - trac_summary
  # - trac_url
  # - trac_number
  #description_template = #{{ trac_number }}: {{ trac_summary }}

  # Here's an example of a bugzilla target.  This will scrape every ticket
  # 1) that is not closed and 2) that rbean@redhat.com is either the
  # owner or reporter or is cc'd on.  Bugzilla instances can be quite different
  # from one another so use this with caution and please report bugs so we can
  # make bugwarrior support more robust!
  [bz.redhat]
  service = bugzilla

  bugzilla.base_uri = bugzilla.redhat.com
  bugzilla.username = rbean@redhat.com
  bugzilla.password = OMG_LULZ

  # You can override how an issue's description is created by entering
  # a one-line Jinja template like the below; in addition to the default
  # taskwarrior issue properties (project, priority, due, etc), the
  # following properties are available for Bugzilla issues:
  # - bugzilla_url
  # - bugzilla_summary
  #description_template = {{ bugzilla_summary }}

  # Here's an example of a megaplan target.
  [my_megaplan]
  service = megaplan

  megaplan.hostname = example.megaplan.ru
  megaplan.login = alice
  megaplan.password = secret
  megaplan.project_name = example

  default_priority = H

  # You can override how an issue's description is created by entering
  # a one-line Jinja template like the below; in addition to the default
  # taskwarrior issue properties (project, priority, due, etc), the
  # following properties are available for Megaplan issues:
  # - megaplan_url
  # - megaplan_id
  # - megaplan_title
  #description_template = #{{ megaplan_id }}: {{ megaplan_title }}

  # Here's an example of a jira project. The ``jira-python`` module is
  # a bit particular, and jira deployments, like Bugzilla, tend to be
  # reasonably customized. So YMMV. The ``base_uri`` must not have a
  # have a trailing slash. In this case we fetch comments and
  # cases from jira assigned to 'ralph' where the status is not closed or
  # resolved.
  [jira_project]
  service = jira
  jira.base_uri = https://jira.example.org
  jira.username = ralph
  jira.password = OMG_LULZ
  jira.query = assignee = ralph and status != closed and status != resolved
  # Set this to your jira major version. We currently support only jira version
  # 4 and 5(the default). You can find your particular version in the footer at
  # the dashboard.
  jira.version = 5

  # You can override how an issue's description is created by entering
  # a one-line Jinja template like the below; in addition to the default
  # taskwarrior issue properties (project, priority, due, etc), the
  # following properties are available for JIRA issues:
  # - jira_summary
  # - jira_url
  # - jira_id
  #description_template = {{ jira_id }}: {{ jira_summary }}

  # Here's an example of a teamlab target.
  [my_teamlab]
  service = teamlab

  teamlab.hostname = teamlab.example.com
  teamlab.login = alice
  teamlab.password = secret
  teamlab.project_name = example_teamlab

  # You can override how an issue's description is created by entering
  # a one-line Jinja template like the below; in addition to the default
  # taskwarrior issue properties (project, priority, due, etc), the
  # following properties are available for Teamlab issues:
  # - teamlab_url
  # - teamlab_id
  # - teamlab_title
  # - teamlab_projectowner_id
  #description_template = #{{ teamlab_id }}: {{ teamlab_title }}

  # Here's an example of a redmine target.
  [my_redmine]
  service = redmine
  redmine.url = http://redmine.example.org/
  redmine.key = c0c4c014cafebabe
  redmine.user_id = 7
  redmine.project_name = redmine

  # You can override how an issue's description is created by entering
  # a one-line Jinja template like the below; in addition to the default
  # taskwarrior issue properties (project, priority, due, etc), the
  # following properties are available for Redmine issues:
  # - redmine_url
  # - redmine_subject
  # - redmine_id
  #description_template = #{{ redmine_id }}: {{ redmine_subject }}

  # Here's an example of an activecollab3 target. This is only valid for
  # activeCollab 3.x, see below for activeCollab 2.x.
  #
  # Obtain your user ID and API url by logging in, clicking on your avatar on
  # the lower left-hand of the page. When on that page, look at the URL. The
  # number that appears after "/user/" is your user ID.
  #
  # On the same page, go to Options and API Subscriptions. Generate a read-only
  # API key and add that to your bugwarriorrc file.
  #
  # Bugwarrior will only gather tasks and subtasks for projects in your "Favorites"
  # list. Note that if you have 10 projects in your favorites list, bugwarrior
  # will make 21 API calls on each run: 1 call to get a list of favorites, then
  # 2 API calls per projects, one for tasks and one for subtasks.

  [activecollab3]
  service = activecollab3
  activecollab3.url = https://ac.example.org/api.php
  activecollab3.key = your-api-key
  activecollab3.user_id = 15

  # You can override how an issue's description is created by entering
  # a one-line Jinja template like the below; in addition to the default
  # taskwarrior issue properties (project, priority, due, etc), the
  # following properties are available for ActiveCollab3 issues:
  # - ac3_body
  # - ac3_name
  # - ac3_permalink
  # - ac3_task_id
  # - ac3_id
  # - ac3_project_id
  # - ac3_type
  # - ac3_created_on
  # - ac3_created_by_id
  #description_template = #{{ac3_id}} - {% if ac3_name %}{{ ac3_name }}{% else %}{{ ac3_body }}{% endif %}

  # Here's an example of an activecollab2 target. Note that this will only work
  # with ActiveCollab 2.x - see above for 3.x.
  #
  # You can obtain your user ID and API url by logging into ActiveCollab and
  # clicking on "Profile" and then "API Settings". When on that page, look
  # at the URL. The integer that appears after "/user/" is your user ID.
  #
  # Projects should be entered in a comma-separated list, with the project
  # id as the key and the name you'd like to use for the project in Taskwarrior
  # entered as the value. For example, if the project ID is 8 and the project's
  # name in ActiveCollab is "Amazing Website" then you might enter 8:amazing_website
  #
  # Note that due to limitations in the ActiveCollab API, there is no simple way
  # to get a list of all tasks you are responsible for in AC. Instead you need to
  # look at each ticket that you are subscribed to and check to see if your
  # user ID is responsible for the ticket/task. What this means is that if you
  # have 5 projects you want to query and each project has 20 tickets, you'll
  # make 100 API requests each time you run `bugwarrior-pull`

  [activecollab2]
  service = activecollab2
  activecollab2.url = http://ac.example.org/api.php
  activecollab2.key = your-api-key
  activecollab2.user_id = 15
  activecollab2.projects = 1:first_project, 5:another_project

  # You can override how an issue's description is created by entering
  # a one-line Jinja template like the below; in addition to the default
  # taskwarrior issue properties (project, priority, due, etc), the
  # following properties are available for ActiveCollab2 issues:
  # - ac2_body
  # - ac2_name
  # - ac2_permalink
  # - ac2_ticket_id
  # - ac2_project_id
  # - ac2_type
  # - ac2_created_on
  # - ac2_created_by_id
  #description_template = #{{ac2_ticket_id}} - {% if ac2_name %}{{ ac2_name }}{% else %}{{ ac2_body }}{% endif %}

.. example

Using
-----

Just run ``bugwarrior-pull``.

It's ideal to create a cron task like::

    */15 * * * *  /usr/bin/bugwarrior-pull

Bugwarrior can emit desktop notifications when it adds or completes issues
to and from your local ``~/.task/`` db.  If your ``~/.bugwarriorrc`` file has
notifications turned on, you'll also need to tell cron which display to use by
adding the following to your crontab::

    DISPLAY=:0
    */15 * * * *  /usr/bin/bugwarrior-pull

Getting bugwarrior
------------------

Installing from the Python Package Index
++++++++++++++++++++++++++++++++++++++++

Installing it from http://pypi.python.org/pypi/bugwarrior is easy with ``pip``::

    $ pip install bugwarrior

Alternatively, you can use ``easy_install`` if you prefer::

    $ easy_install bugwarrior

Installing from Source
++++++++++++++++++++++

You can find the source on github at http://github.com/ralphbean/bugwarrior.
Either fork/clone if you plan to do development on bugwarrior, or you can simply
download the latest tarball::

    $ wget https://github.com/ralphbean/bugwarrior/tarball/master -O bugwarrior-latest.tar.gz
    $ tar -xzvf bugwarrior-latest.tar.gz
    $ cd ralphbean-bugwarrior-*
    $ python setup.py install

Hacking on It
+++++++++++++

You should install the `virtualenv <https://pypi.python.org/pypi/virtualenv>`_
tool for python.  (I use a wrapper for it called `virtualenvwrapper
<https://pypi.python.org/pypi/virtualenvwrapper>`_ which is awesome but not
required.)  Virtualenv will help isolate your dependencies from the rest of
your system.

::

    $ sudo yum install python-virtualenv git
    $ mkdir -p ~/virtualenvs/
    $ virtualenv ~/virtualenvs/bugwarrior

You should now have a virtualenv in a ``~/virtualenvs/`` directory.
To use it, you need to "activate" it like this::

    $ source ~/virtualenv/bugwarrior/bin/activate
    (bugwarrior)$ which python

At any time, you can deactivate it by typing ``deactivate`` at the command
prompt.

Next step -- get the code!

::

    (bugwarrior)$ git clone git@github.com:ralphbean/bugwarrior.git
    (bugwarrior)$ cd bugwarrior
    (bugwarrior)$ python setup.py develop
    (bugwarrior)$ which bugwarrior-pull

This will actually run it.. be careful and back up your task directory!

::

    (bugwarrior)$ bugwarrior-pull


Contributors
------------

- Ralph Bean (primary author)
- Justin Forest (contributed support for RedMine, TeamLab, and MegaPlan, as
  well as some unicode help)
- Tycho Garen (contributed support for Jira)
- Kosta Harlan (contributed support for ActiveCollab 2.x/3.x, notifications,
  and experimental taskw support)
- Luke Macken (contributed some code cleaning)
- James Rowe (contributed to the docs)
