How to Configure
================

First, add a file named named ``.bugwarriorrc`` to your home folder.
This file must include at least a ``[general]`` section including
the following option:

* ``targets``: A comma-separated list of *other* section names to use
  as task sources.

Optional options include:

* ``taskrc``: Specify which TaskRC configuration file to use.  By default,
  will use the system default (usually ``~/.taskrc``).
* ``shorten``: Set to ``True`` to shorten links.
* ``legacy_matching``: Set to ``False`` to instruct Bugwarrior to match
  issues using only the issue's unique identifiers (rather than matching
  on description).
* ``log.level``: Set to one of ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``,
  ``CRITICAL``, or ``DISABLED`` to control the logging verbosity.  By
  default, this is set to ``DEBUG``.
* ``log.file``: Set to the path at which you would like logging messages
  written.  By default, logging messages will be written to stderr.
* ``annotation_length``: Import maximally this number of characters
  of incoming annotations.  Default: 45.

A more-detailed example configuration can be found at :ref:`example_configuration`.

.. _common_configuration_options:

Common Service Configuration Options
------------------------------------

All services support the following configuration options in addition
to any specified service features or settings specified in the
service example:

* ``only_if_assigned``: Only import issues assigned to the specified
  user.
* ``also_unassigned``: Same as above, but also create tasks for issues
  that are not assigned to anybody.
* ``default_priority``: Assign this priority ('L', 'M', or 'H') to
  newly-imported issues.
* ``add_tags``: Add these tags to newly-imported issues.
* ``description_template``: Build the issue description following this
  template.  See `Description Templates`_ for more details.

.. _description_templates:

Description Templates
---------------------

By default, Bugwarrior will import issues with a fairly verbose description
template looking something like this::

    (BW)Issue#10 - Fix perpetual motion machine .. http://media.giphy.com/media/LldEzRPqyo2Yg/giphy.gif

but depending upon your workflow, the information presented may not be
useful to you.

To help users build descriptions that suit their needs, all services allow
one to specify a ``description_template`` configuration option, in which
one can enter a one-line Jinja template.  The context available includes
all Taskwarrior fields and all UDAs (see section named 'Provided UDA Fields'
for each service) defined for the relevant service.

For example, to pull-in github issues assigned to
`@ralphbean <https://github.com/ralphbean>`_, setting the issue description
such that it is composed of only the github issue number and title, you could
create a service entry like this::

    [ralphs_github_account]
    service = github
    github.username = ralphbean
    description_template = {{githubnumber}}: {{githubtitle}}

Password Management
-------------------

You need not store your password in plain text in your `~/.bugwarriorrc` file; 
you can enter the following values to control where to gather your password
from:

* ``password = @oracle:use_keyring``: Retrieve a password from a keyring.
* ``password = @oracle:ask_password``: Ask for a password at runtime.
* ``password = @oracle:eval:<command>`` Use the output of <command> as the password.

Hooks
-----

Use hooks to run commands prior to importing from bugwarrior-pull.
bugwarrior-pull will run the commands in the order that they are specified
below.

To use hooks, add a ``[hooks]`` section to your configuration, mapping
the hook you'd like to use with a comma-separated list of scripts to execute.

::

  [hooks]
  pre_import = /home/someuser/backup.sh, /home/someuser/sometask.sh

Hook options:

* ``pre_import``: The pre_import hook is invoked after all issues have been pulled
  from remote sources, but before they are synced to the TW db. If your
  pre_import script has a non-zero exit code, the ``bugwarrior-pull`` command will
  exit early.


Notifications
-------------

Add a ``[notifications]`` section to your configuration to receive notifications
when a bugwarrior pull runs, and when issues are created, updated, or deleted
by ``bugwarrior-pull``::

  [notifications]
  notifications = True
  backend = growlnotify
  finished_querying_sticky = False
  task_crud_sticky = True

Backend options:

+------------------+------------------+-------------------------+
| Backend Name     | Operating System | Required Python Modules |
+==================+==================+=========================+
| ``growlnotify``  | MacOS X          | ``gntp``                |
+------------------+------------------+-------------------------+
| ``gobject``      | Linux            | ``gobject``             |
+------------------+------------------+-------------------------+
| ``pynotify``     | Linux            | ``pynotify``            |
+------------------+------------------+-------------------------+

.. note::

   The ``finished_querying_sticky`` and ``task_crud_sticky`` options
   have no effect if you are using a notification backend other than
   ``growlnotify``.
