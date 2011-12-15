bugwarrior - Pull tickets from github, bitbucket, and trac into taskwarrior
===========================================================================

.. split here

This is a command line utility for updating your local `taskwarrior
<http://taskwarrior.org>`_ database from you forge issue trackers.

Getting bugwarrior
-------------

Installing
++++++++++

Installing it from http://pypi.python.org/pypi/bugwarrior is easy with ``pip``::

    $ pip install bugwarrior

The Source
++++++++++

You can find the source on github at http://github.com/ralphbean/bugwarrior


Configuring
-----------

Create a ``~/.bugwarriorrc`` file with the following contents::

  [github]
  github_user = YOUR_USERNAME

  [bitly]
  api_user = YOUR_USERNAME
  api_key = R_3c223c39de2d675

Using
-----

Just run ``bugwarrior-pull``.

It's ideal to create a cron task like::

    0 * * * *  /usr/bin/bugwarrior-pull 2>&1 | /usr/bin/logger

