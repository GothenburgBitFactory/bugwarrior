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

  # General stuff.
  [general]
  # Here you define a comma separated list of targets.  Each of them must have a
  # section below determining their properties, how to query them, etc.  The name
  # is just a symbol, and doesn't have any functional importance.
  targets = my_github, my_bitbucket, paj_bitbucket, moksha_trac, bz.redhat

  # log.level specifices the verbosity.  The default is DEBUG.
  # log.level can be one of DEBUG, INFO, WARNING, ERROR, CRITICAL, DISABLED
  #log.level = DEBUG

  # If log.file is specified, output will be redirected there.  If it remains
  # unspecified, output is sent to sys.stderr
  #log.file = /var/log/bugwarrior.log

  # The bitly username and api key are used to shorten URLs to the issues for your
  # task list.  If you leave these options commented out, then the full URLs
  # will be used in your task list.
  #bitly.api_user = YOUR_USERNAME
  #bitly.api_key = YOUR_API_KEY

  # This is an experimental mode where bugwarrior will query all of your
  # online sources simultaneously.  It works as far as I've tested it, so
  # give it a try.  Please backup your ~/.task/ directory first and report
  # any problems if you encounter them at
  # https://github.com/ralphbean/bugwarrior/issues
  #multiprocessing = False

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
  username = ralphbean
  default_priority = H

  # Note that login and username can be different.  I can login as me, but
  # scrape issues from an organization's repos.
  login = ralphbean
  passw = OMG_LULZ

  # This is the same thing, but for bitbucket.  Each target entry must have a
  # 'service' attribute which must be one of the supported services (like
  # 'github', 'bitbucket', 'trac', etc...).
  [my_bitbucket]
  service = bitbucket
  username = ralphbean
  default_priority = M

  # Here's another bitbucket one.  Here we want to scrape the issues from repos of
  # another user, but only include them in the taskwarrior db if they're assigned
  # to me.
  [paj_bitbucket]
  service = bitbucket
  username = paj
  only_if_assigned = ralphbean
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

  # Here's an example of a megaplan target.
  [my_megaplan]
  service = megaplan

  hostname = example.megaplan.ru
  login = alice
  password = secret

  default_priority = H
  project_name = example

  # Here's an example of a jira project. The ``jira-python`` module is
  # a bit particular, and jira deployments, like Bugzilla, tend to be
  # reasonably customized. So YMMV. The ``base_uri`` must not have a
  # have a trailing slash. In this case we fetch comments and
  # cases from jira assigned to 'ralph' where the status is not closed or
  # resolved.
  [jira.project]
  service = jira
  jira.base_uri = https://jira.example.org
  jira.username = ralph
  jira.password = OMG_LULZ
  jira.query = assignee = ralph and status != closed and status != resolved
  jira.project_prefix = Programming.

  # Here's an example of a teamlab target.
  [my_teamlab]
  service = teamlab

  hostname = teamlab.example.com
  login = alice
  password = secret

  project_name = example_teamlab

  # Here's an example of a redmine target.
  [my_redmine]
  service = redmine
  url = http://redmine.example.org/
  key = c0c4c014cafebabe
  user_id = 7
  project_name = redmine

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
  url = https://ac.example.org/api.php
  key = your-api-key
  user_id = 15

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
  url = http://ac.example.org/api.php
  key = your-api-key
  user_id = 15
  projects = 1:first_project, 5:another_project


.. example

Using
-----

Just run ``bugwarrior-pull``.

It's ideal to create a cron task like::

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


Contributors
------------

- Ralph Bean (primary author)
- Justin Forest (contributed support for RedMine, TeamLab, and MegaPlan, as
  well as some unicode help)
- Tycho Garen (contributed support for Jira)
- Kosta Harlan (contributed support for ActiveCollab 2.x/3.x, and notifications)
- Luke Macken (contributed some code cleaning)
- James Rowe (contributed to the docs)
