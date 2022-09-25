bugwarrior - Pull tickets from github, bitbucket, bugzilla, jira, trac, and others into taskwarrior
===================================================================================================

.. split here

``bugwarrior`` is a command line utility for updating your local `taskwarrior <http://taskwarrior.org>`_ database from your forge issue trackers.

It currently supports the following remote resources:

.. class:: services

- `ActiveCollab 2 <https://www.activecollab.com>`_
- `ActiveCollab 4 <https://www.activecollab.com>`_
- `Azure DevOps <https://azure.microsoft.com/en-us/services/devops/>`_
- `Bitbucket <https://bitbucket.org>`_
- `Bugzilla <https://www.bugzilla.org/>`_
- `Debian Bug Tracking System (BTS) <https://bugs.debian.org/>`_
- `Gerrit <https://www.gerritcodereview.com/>`_
- `Git-Bug <https://github.com/MichaelMure/git-bug>`_
- `Github <https://github.com>`_
- `Gitlab <https://gitlab.com>`_
- `Gmail <https://www.google.com/gmail/about/>`_
- `Jira <https://www.atlassian.com/software/jira/overview>`_
- `Kanboard <https://kanboard.org/>`_
- `Nextcloud Deck <https://github.com/nextcloud/deck>`_
- `Pagure <https://pagure.io/>`_
- `Phabricator <http://phabricator.org/>`_
- `Pivotal Tracker <https://www.pivotaltracker.com/>`_
- `Redmine <https://www.redmine.org/>`_
- `Taiga <https://taiga.io>`_
- `Teamlab <https://www.teamlab.com/>`_
- `Teamwork Projects <https://www.teamwork.com/>`_
- `Trac <https://trac.edgewall.org/>`_
- `Trello <https://trello.com/>`_
- `VersionOne <http://www.versionone.com/>`_
- `YouTrack <https://www.jetbrains.com/youtrack/>`_

Documentation
-------------

For information on how to install and use bugwarrior, `read the docs
<https://bugwarrior-docs.readthedocs.io>`_ on RTFD.

Build Status
------------

.. |develop| image:: https://github.com/ralphbean/bugwarrior/actions/workflows/bugwarrior.yml/badge.svg?branch=develop
   :alt: Build Status - develop branch

+----------+-----------+
| Branch   | Status    |
+==========+===========+
| develop  | |develop| |
+----------+-----------+


Contributors
------------

- Ralph Bean (primary author)
- Ben Boeckel (contributed support for Gitlab)
- Justin Forest (contributed support for RedMine, TeamLab, and MegaPlan, as
  well as some unicode help)
- Tycho Garen (contributed support for Jira)
- Kosta Harlan (contributed support for activeCollab, notifications,
  and experimental taskw support)
- Luke Macken (contributed some code cleaning)
- James Rowe (contributed to the docs)
- Adam Coddington (anti-entropy crusader)
- Iain R. Learmonth (contributed support for the Debian BTS and maintains the
  Debian package)
- BinaryBabel (contributed support for YouTrack)
- Matthew Cengia (contributed extra support for Trello)
- Andrew Demas (contributed support for PivotalTracker)
- Florian Preinstorfer (contributed support for Kanboard)
- Lena Brüder (contributed support for Nextcloud Deck)
