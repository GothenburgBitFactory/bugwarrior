.. _example_configuration:

Example Configuration
======================

.. example

::

    # Example bugwarriorrc

    # General stuff.
    [general]
    # Here you define a comma separated list of targets.  Each of them must have a
    # section below determining their properties, how to query them, etc.  The name
    # is just a symbol, and doesn't have any functional importance.
    targets = my_github, my_bitbucket, paj_bitbucket, moksha_trac, bz.redhat, pivotaltracker

    # If unspecified, the default taskwarrior config will be used.
    #taskrc = /path/to/.taskrc

    # Setting this to true will shorten links with http://da.gd/
    #shorten = False

    # Setting this to True will include a link to the ticket in the description
    inline_links = False

    # Setting this to True will include a link to the ticket as an annotation
    annotation_links = True

    # Setting this to True will include issue comments and author name in task
    # annotations
    annotation_comments = True

    # Setting this to False will strip newlines from comment annotations
    annotation_newlines = False

    # log.level specifies the verbosity.  The default is DEBUG.
    # log.level can be one of DEBUG, INFO, WARNING, ERROR, CRITICAL, DISABLED
    #log.level = DEBUG

    # If log.file is specified, output will be redirected there.  If it remains
    # unspecified, output is sent to sys.stderr
    #log.file = /var/log/bugwarrior.log

    # Configure the default description or annotation length.
    #annotation_length = 45

    # Use hooks to run commands prior to importing from bugwarrior-pull.
    # bugwarrior-pull will run the commands in the order that they are specified
    # below.
    #
    # pre_import: The pre_import hook is invoked after all issues have been pulled
    # from remote sources, but before they are synced to the TW db. If your
    # pre_import script has a non-zero exit code, the `bugwarrior-pull` command will
    # exit early.
    [hooks]
    pre_import = /home/someuser/backup.sh, /home/someuser/sometask.sh

    # This section is for configuring notifications when bugwarrior-pull runs,
    # and when issues are created, updated, or deleted by bugwarrior-pull.
    # Three backends are currently supported:
    #
    #  - growlnotify (v2)   Mac OS X   "gntp" must be installed
    #  - gobject            Linux      python gobject must be installed
    #
    # To configure, adjust the settings below.  Note that neither of the #
    # "sticky" options have any effect on Linux.  They only work for
    # growlnotify.
    #[notifications]
    # notifications = True
    # backend = growlnotify
    # finished_querying_sticky = False
    # task_crud_sticky = True
    # only_on_new_tasks = True


    # This is a github example.  It says, "scrape every issue from every repository
    # on http://github.com/ralphbean.  It doesn't matter if ralphbean owns the issue
    # or not."
    [my_github]
    service = github
    github.default_priority = H
    github.add_tags = open_source

    # This specifies that we should pull issues from repositories belonging
    # to the 'ralphbean' github account.  See the note below about
    # 'github.username' and 'github.login'.  They are different, and you need
    # both.
    github.username = ralphbean

    # I want taskwarrior to include issues from all my repos, except these
    # two because they're spammy or something.
    github.exclude_repos = project_bar,project_baz

    # Working with a large number of projects, instead of excluding most of them I
    # can also simply include just a limited set.
    github.include_repos = project_foo,project_foz

    # Note that login and username can be different:  I can login as me, but
    # scrape issues from an organization's repos.
    #
    # - 'github.login' is the username you ask bugwarrior to
    #   login as.  Set it to your account.
    # - 'github.username' is the github entity you want to pull
    #   issues for.  It could be you, or some other user entirely.
    github.login = ralphbean
    github.password = OMG_LULZ


    # Here's an example of a trac target.
    [moksha_trac]
    service = trac

    trac.base_uri = fedorahosted.org/moksha
    trac.username = ralph
    trac.password = OMG_LULZ

    trac.only_if_assigned = ralph
    trac.also_unassigned = True
    trac.default_priority = H
    trac.add_tags = work

    # Here's an example of a megaplan target.
    [my_megaplan]
    service = megaplan

    megaplan.hostname = example.megaplan.ru
    megaplan.login = alice
    megaplan.password = secret
    megaplan.project_name = example

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
    jira.add_tags = enterprisey,work

    # Here's an example of a phabricator target
    [my_phabricator]
    service = phabricator
    # No need to specify credentials.  They are gathered from ~/.arcrc

    # Here's an example of a teamlab target.
    [my_teamlab]
    service = teamlab

    teamlab.hostname = teamlab.example.com
    teamlab.login = alice
    teamlab.password = secret
    teamlab.project_name = example_teamlab

    # Here's an example of a redmine target.
    [my_redmine]
    service = redmine
    redmine.url = http://redmine.example.org/
    redmine.key = c0c4c014cafebabe
    redmine.user_id = 7
    redmine.project_name = redmine
    redmine.add_tags = chiliproject

    [activecollab]
    service = activecollab
    activecollab.url = https://ac.example.org/api.php
    activecollab.key = your-api-key
    activecollab.user_id = 15
    activecollab.add_tags = php

    [activecollab2]
    service = activecollab2
    activecollab2.url = http://ac.example.org/api.php
    activecollab2.key = your-api-key
    activecollab2.user_id = 15
    activecollab2.projects = 1:first_project, 5:another_project

    [my_gmail]
    service = gmail
    gmail.query = label:action OR label:readme
    gmail.login_name = you@example.com

    [pivotaltracker]
    service = pivotaltracker
    pivotaltracker.token = your-api-key
    pivotaltracker.version = v5
    pivotaltracker.user_id = your-user-id
    pivotaltracker.account_ids = first_account_id,second_account_id
    pivotaltracker.only_if_assigned = True
    pivotaltracker.also_unassigned = False
    pivotaltracker.only_if_author = False
    pivotaltracker.import_labels_as_tags = True
    pivotaltracker.label_template = pivotal_{{label}}
    pivotaltracker.import_blockers = True
    pivotaltracker.blocker_template = "Description: {{description}} State: {{resolved}}\n"
    pivotaltracker.annotation_comments = True
    pivotaltracker.annotation_template = "status: {{completed}} - MYDESC {{description}}"
    piivotaltracker.exclude_projects = first_project_id,second_project_id
    pivotaltracker.exclude_stories = first_story_id,second_story_id
    pivotaltracker.exclude_tags = "wont fix", "should fix"
    pivotaltracker.query = mywork:1234 -has:label
