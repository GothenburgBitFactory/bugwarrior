bugwarrior - Pull tickets from github, bitbucket, and trac into taskwarrior
===========================================================================

.. split here

``bugwarrior`` is a command line utility for updating your local `taskwarrior <http://taskwarrior.org>`_ database from your forge issue trackers.

It currently supports the following remote resources:

 - `github <http://github.com>`_
 - `bitbucket <http://bitbucket.org>`_
 - `trac <http://trac.edgewall.org/>`_
 - `bugzilla <http://www.bugzilla.org/>`_

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

  # This is a github example.  It says, "scrape every issue from every repository
  # on http://github.com/ralphbean.  It doesn't matter if ralphbean owns the issue
  # or not."
  [my_github]
  service = github
  username = ralphbean
  default_priority = H

  # This is the same thing, but for bitbucket.  Each target entry must have a
  # 'service' attribute which must be one of 'github', 'bitbucket', or 'trac'.
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
  # 1) that is not closed and 2) for which rbean@redhat.com is either the
  # owner or reporter or is cc'd on.  Bugzilla instances can be quite different
  # from one another so use this with caution and please report bugs so we can
  # make bugwarrior support more robust!
  [bz.redhat]
  service = bugzilla

  bugzilla.base_uri = bugzilla.redhat.com
  bugzilla.username = rbean@redhat.com
  bugzilla.password = OMG_LULZ


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

