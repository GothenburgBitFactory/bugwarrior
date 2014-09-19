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
 - `activecollab <http://www.activecollab.com>`_ (2.x and 4.x)
 - `phabricator <http://phabricator.org/>`_

Documentation
-------------

For information on how to install and use bugwarrior, read `the docs
<http://bugwarrior.rtfd.org>`_ on RTFD.

Build Status
------------

.. |master| image:: https://secure.travis-ci.org/ralphbean/bugwarrior.png?branch=master
   :alt: Build Status - master branch
   :target: http://travis-ci.org/#!/ralphbean/bugwarrior

.. |develop| image:: https://secure.travis-ci.org/ralphbean/bugwarrior.png?branch=develop
   :alt: Build Status - develop branch
   :target: http://travis-ci.org/#!/ralphbean/bugwarrior

+----------+-----------+
| Branch   | Status    |
+==========+===========+
| master   | |master|  |
+----------+-----------+
| develop  | |develop| |
+----------+-----------+


Contributors
------------

- Ralph Bean (primary author)
- Justin Forest (contributed support for RedMine, TeamLab, and MegaPlan, as
  well as some unicode help)
- Tycho Garen (contributed support for Jira)
- Kosta Harlan (contributed support for activeCollab, notifications,
  and experimental taskw support)
- Luke Macken (contributed some code cleaning)
- James Rowe (contributed to the docs)
- Adam Coddington (anti-entropy crusader)
