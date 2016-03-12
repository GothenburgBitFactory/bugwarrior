Getting bugwarrior
==================

Installing from the Python Package Index
----------------------------------------

Installing it from http://pypi.python.org/pypi/bugwarrior is easy with
:command:`pip`::

    $ pip install bugwarrior

Alternatively, you can use :command:`easy_install` if you prefer::

    $ easy_install bugwarrior

By default, ``bugwarrior`` will be installed with support for the following
services: Bitbucket, Bugzilla, Github, Gitlab, Pagure, Phabricator, Redmine,
Teamlab, Track and Versionone. There is optional support for Jira, Megaplan.ru
and Active Collab but those require extra dependencies that are installed by
specifying ``bugwarrior[service]`` in the commands above. For example, if you
want to use bugwarrior with Jira::

    $ pip install bugwarrior[jira]


Installing from Source
----------------------

You can find the source on github at http://github.com/ralphbean/bugwarrior.
Either fork/clone if you plan to do development on bugwarrior, or you can simply
download the latest tarball::

    $ wget https://github.com/ralphbean/bugwarrior/tarball/master -O bugwarrior-latest.tar.gz
    $ tar -xzvf bugwarrior-latest.tar.gz
    $ cd ralphbean-bugwarrior-*
    $ python setup.py install

Installing from Distribution Packages
-------------------------------------

bugwarrior has been packaged for Fedora.  You can install it with the standard
:command:`dnf` (:command:`yum`) package management tools as follows::

    $ sudo dnf install bugwarrior
