bugwarrior - Pull tickets from github, bitbucket, bugzilla, jira, trac, and others into taskwarrior
===================================================================================================

.. split here

``bugwarrior`` is a command line utility for updating your local `taskwarrior <http://taskwarrior.org>`_ database from your forge issue trackers.

It currently supports the following remote resources:

 - `activecollab <https://www.activecollab.com>`_ (2.x and 4.x)
 - `bitbucket <https://bitbucket.org>`_
 - `bugzilla <https://www.bugzilla.org/>`_
 - `Debian BTS <https://bugs.debian.org/>`_
 - `gerrit <https://www.gerritcodereview.com/>`_
 - `github <https://github.com>`_ (api v3)
 - `gitlab <https://gitlab.com>`_ (api v3)
 - `gmail <https://www.google.com/gmail/about/>`_
 - `jira <https://www.atlassian.com/software/jira/overview>`_
 - `kanboard <https://kanboard.org/>`_
 - `pagure <https://pagure.io/>`_
 - `phabricator <http://phabricator.org/>`_
 - `Pivotal Tracker <https://www.pivotaltracker.com/>`_
 - `redmine <https://www.redmine.org/>`_
 - `taiga <https://taiga.io>`_
 - `teamlab <https://www.teamlab.com/>`_
 - `trac <https://trac.edgewall.org/>`_
 - `trello <https://trello.com/>`_
 - `versionone <http://www.versionone.com/>`_
 - `youtrack <https://www.jetbrains.com/youtrack/>`_

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
