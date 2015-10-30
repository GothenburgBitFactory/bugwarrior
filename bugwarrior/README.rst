bugwarrior - Pull tickets from github, bitbucket, bugzilla, jira, trac, and others into taskwarrior
===================================================================================================

.. split here

``bugwarrior`` is a command line utility for updating your local `taskwarrior <http://taskwarrior.org>`_ database from your forge issue trackers.

It currently supports the following remote resources:

 - `github <https://github.com>`_ (api v3)
 - `gitlab <https://gitlab.com>`_ (api v3)
 - `bitbucket <https://bitbucket.org>`_
 - `pagure <https://pagure.io/>`_
 - `bugzilla <https://www.bugzilla.org/>`_
 - `trac <https://trac.edgewall.org/>`_
 - `megaplan <https://www.megaplan.ru/>`_
 - `teamlab <https://www.teamlab.com/>`_
 - `redmine <https://www.redmine.org/>`_
 - `jira <https://www.atlassian.com/software/jira/overview>`_
 - `activecollab <https://www.activecollab.com>`_ (2.x and 4.x)
 - `phabricator <http://phabricator.org/>`_
 - `versionone <http://www.versionone.com/>`_

Documentation
-------------

For information on how to install and use bugwarrior, read `the docs
<https://bugwarrior.readthedocs.org>`_ on RTFD.

Build Status
------------

.. |master| image:: https://secure.travis-ci.org/ralphbean/bugwarrior.png?branch=master
   :alt: Build Status - master branch
   :target: https://travis-ci.org/#!/ralphbean/bugwarrior

.. |develop| image:: https://secure.travis-ci.org/ralphbean/bugwarrior.png?branch=develop
   :alt: Build Status - develop branch
   :target: https://travis-ci.org/#!/ralphbean/bugwarrior

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
- Ben Boeckel(contributed support for Gitlab)
- Justin Forest (contributed support for RedMine, TeamLab, and MegaPlan, as
  well as some unicode help)
- Tycho Garen (contributed support for Jira)
- Kosta Harlan (contributed support for activeCollab, notifications,
  and experimental taskw support)
- Luke Macken (contributed some code cleaning)
- James Rowe (contributed to the docs)
- Adam Coddington (anti-entropy crusader)
