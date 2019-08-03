Getting bugwarrior
==================

.. _requirements:

Requirements
------------

To use bugwarrior, you need python 3 and taskwarrior. Upon installation, the
setup script will automatically download and install missing python
dependencies.

Note that some of those dependencies have a C extension module (e.g. the
``cryptography`` package).  If those packages are not yet present on your
system, the setup script will try to build them locally, for which you will
need a C compiler (e.g. ``gcc``) and the necessary header files (python and,
for the cryptography package, openssl).
A convenient way to install those is to use your usual package manager
(``dnf``, ``yum``, ``apt``, etc).
Header files are installed from development packages (e.g.  ``python-devel``
and ``openssl-devel`` on Fedora or ``python-dev`` ``libssl-dev`` on Debian).

Installing from the Python Package Index
----------------------------------------

.. highlight:: console

Installing from https://pypi.python.org/pypi/bugwarrior is easy with
:command:`pip`::

    $ pip install bugwarrior

By default, ``bugwarrior`` will be installed with support for the following
services: Bitbucket, Github, Gitlab, Pagure, Phabricator, Redmine, Teamlab, and
Versionone. There is optional support for Jira, Megaplan.ru, Active Collab,
Debian BTS, Trac, Bugzilla, and but those require extra dependencies that are
installed by specifying ``bugwarrior[service]`` in the commands above. For
example, if you want to use bugwarrior with Jira::

    $ pip install "bugwarrior[jira]"

The following extra dependency sets are available:

- keyring (See also `linux installation instructions <https://github.com/jaraco/keyring#linux>`_.)
- jira
- megaplan
- activecollab
- bts
- trac
- bugzilla
- gmail

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
