bugwarrior - Pull tickets from github, bitbucket, and trac into taskwarrior
===========================================================================

.. split here

This is a command line utility for updating your local `taskwarrior
<http://taskwarrior.org>`__ database from your forge issue trackers.

Getting bugwarrior
------------------

Installing
++++++++++

Installing it from http://pypi.python.org/pypi/bugwarrior is easy with ``pip``::

    $ pip install bugwarrior

The Source
++++++++++

You can find the source on github at http://github.com/ralphbean/bugwarrior


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
  targets = my_github, my_bitbucket, paj_bitbucket, moksha_trac

  # The bitly username and api key are used to shorten URLs to the issues for your
  # task list.
  bitly.api_user = YOUR_USERNAME
  bitly.api_key = YOUR_API_KEY

  # This is a github example.  It says, "scrape every issue from every repository
  # on http://github.com/ralphbean.  It doesn't matter if ralphbean owns the issue
  # or not."
  [my_github]
  service = github
  username = ralphbean

  # This is the same thing, but for bitbucket.  Each target entry must have a
  # 'service' attribute which must be one of 'github', 'bitbucket', or 'trac'.
  [my_bitbucket]
  service = bitbucket
  username = ralphbean

  # Here's another bitbucket one.  Here we want to scrape the issues from repos of
  # another user, but only include them in the taskwarrior db if they're assigned
  # to me.
  [paj_bitbucket]
  service = bitbucket
  username = paj
  only_if_assigned = ralphbean

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


.. example

Using
-----

Just run ``bugwarrior-pull``.

It's ideal to create a cron task like::

    0 * * * *  /usr/bin/bugwarrior-pull 2>&1 | /usr/bin/logger

