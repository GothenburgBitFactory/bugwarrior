How to Configure
================

First, add a file named ``.config/bugwarrior/bugwarriorrc`` to your home
folder.  This file must include at least a ``[general]`` section including the
following option:

* ``targets``: A comma-separated list of *other* section names to use
  as task sources.

Optional options include:

* ``taskrc``: Specify which TaskRC configuration file to use.  By default,
  will use the system default (usually ``~/.taskrc``).
* ``shorten``: Set to ``True`` to shorten links.
* ``inline_links``: When ``False``, links are appended as an annotation.
  Defaults to ``True``.
* ``annotation_links``: When ``True`` will include a link to the ticket as an
  annotation. Defaults to ``False``.
* ``annotation_comments``: When ``False`` skips putting issue comments into
  annotations. Defaults to ``True``.
* ``annotation_newlines``: When ``False`` strips newlines from comments in
  annotations. Defaults to ``False``.
* ``log.level``: Set to one of ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``,
  ``CRITICAL``, or ``DISABLED`` to control the logging verbosity.  By
  default, this is set to ``INFO``.
* ``log.file``: Set to the path at which you would like logging messages
  written.  By default, logging messages will be written to stderr.
* ``annotation_length``: Import maximally this number of characters
  of incoming annotations.  Default: 45.
* ``description_length``: Use maximally this number of characters in the
  description. Default: 35.
* ``merge_annotations``: If ``False``, bugwarrior won't bother with adding
  annotations to your tasks at all.  Default: ``True``.
* ``merge_tags``: If ``False``, bugwarrior won't bother with adding
  tags to your tasks at all.  Default: ``True``.
* ``replace_tags``: If ``True``, bugwarrior will delete all tags prior to
  fetching new ones, except those listed in ``static_tags``. Only work if
  merge_tags is ``True``. Default: ``False``.
* ``static_tags``: A comma separated list of tags that shouldn't be *removed* by
  bugwarrior. Use for tags that you want to keep when replace_tags is set to
  ``True``.
* ``static_fields``: A comma separated list of attributes that shouldn't be
  *updated* by bugwarrior.  Use for values that you want to tune manually.
  Default: ``priority``.

In addition to the ``[general]`` section, sections may be named
``[flavor.myflavor]`` and may be selected using the ``--flavor`` option to
``bugwarrior-pull``. This section will then be used rather than the
``[general]`` section.

A more-detailed example configuration can be found at
:ref:`example_configuration`.


.. _common_configuration_options:

Common Service Configuration Options
------------------------------------

All services support common configuration options in addition
to their service-specific features.
These configuration options are meant to be prefixed with the service name,
e.g. ``github.add_tags``, or ``gitlab.default_priority``.

The following options are supported:

* ``SERVICE.only_if_assigned``: If set to a username, only import issues
  assigned to the specified user.
* ``SERVICE.also_unassigned``: If set to ``True`` and ``only_if_assigned`` is
  set, then also create tasks for issues that are not assigned to anybody.
  Defaults to ``False``.
* ``SERVICE.default_priority``: Assign this priority ('L', 'M', or 'H') to
  newly-imported issues. Defaults to ``M``.
* ``SERVICE.add_tags``: A comma-separated list of tags to add to an issue.  In
  most cases, plain strings will suffice, but you can also specify
  templates.  See the section `Field Templates`_ for more information.

.. _field_templates:

Field Templates
---------------

By default, Bugwarrior will import issues with a fairly verbose description
template looking something like this::

    (BW)Issue#10 - Fix perpetual motion machine .. http://media.giphy.com/media/LldEzRPqyo2Yg/giphy.gif

but depending upon your workflow, the information presented may not be
useful to you.

To help users build descriptions that suit their needs, all services allow
one to specify a ``SERVICE.description_template`` configuration option, in
which one can enter a one-line Jinja template.  The context available includes
all Taskwarrior fields and all UDAs (see section named 'Provided UDA Fields'
for each service) defined for the relevant service.

.. note::

   Jinja templates can be very complex.  For more details about
   Jinja templates, please consult
   `Jinja's Template Documentation <http://jinja.pocoo.org/docs/templates/>`_.

For example, to pull-in Github issues assigned to
`@ralphbean <https://github.com/ralphbean>`_, setting the issue description
such that it is composed of only the Github issue number and title, you could
create a service entry like this::

    [ralphs_github_account]
    service = github
    github.username = ralphbean
    github.description_template = {{githubnumber}}: {{githubtitle}}

You can also use this tool for altering the generated value of any other
Taskwarrior record field by using the same kind of template.

Uppercasing the project name for imported issues::

    SERVICE.project_template = {{project|upper}}

You can also use this feature to override the generated value of any field.
This example causes imported issues to be assigned to the 'Office' project
regardless of what project was assigned by the service itself::

    SERVICE.project_template = Office

Password Management
-------------------

You need not store your password in plain text in your `bugwarriorrc` file; 
you can enter the following values to control where to gather your password
from:

``password = @oracle:use_keyring``
  Retrieve a password from the system keyring.  The ``bugwarrior-vault``
  command line tool can be used to manage your passwords as stored in your
  keyring (say to reset them or clear them).  Extra dependencies must be
  installed with `pip install bugwarrior[keyring]` to enable this feature.
``password = @oracle:ask_password``
  Ask for a password at runtime.
``password = @oracle:eval:<command>``
  Use the output of <command> as the password. For instance, to integrate
  bugwarrior with the password manager `pass <https://www.passwordstore.org/>`_
  you can use ``@oracle:eval:pass my/password``.


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
  only_on_new_tasks = True

Backend options:

+------------------+------------------+-------------------------+
| Backend Name     | Operating System | Required Python Modules |
+==================+==================+=========================+
| ``growlnotify``  | MacOS X          | ``gntp``                |
+------------------+------------------+-------------------------+
| ``gobject``      | Linux            | ``gobject``             |
+------------------+------------------+-------------------------+

.. note::

   The ``finished_querying_sticky`` and ``task_crud_sticky`` options
   have no effect if you are using a notification backend other than
   ``growlnotify``.


Configuration files
-------------------

bugwarrior will look at the following paths and read its configuration from the
first existing file in this order:

* :file:`~/.config/bugwarrior/bugwarriorrc`
* :file:`~/.bugwarriorrc`
* :file:`/etc/xdg/bugwarrior/bugwarriorrc`

The default paths can be altered using the environment variables
:envvar:`BUGWARRIORRC`, :envvar:`XDG_CONFIG_HOME` and
:envvar:`XDG_CONFIG_DIRS`.


Environment Variables
---------------------

.. envvar:: BUGWARRIORRC

This overrides the default RC file.

.. envvar:: XDG_CONFIG_HOME

By default, :program:`bugwarrior` looks for a configuration file named
``$XDG_CONFIG_HOME/bugwarrior/bugwarriorrc``.  If ``$XDG_CONFIG_HOME`` is
either not set or empty, a default equal to ``$HOME/.config`` is used.

.. envvar:: XDG_CONFIG_DIRS

If it can't find a user-specific configuration file (either
``$XDG_CONFIG_HOME/bugwarrior/bugwarriorrc`` or ``$HOME/.bugwarriorrc``),
:program:`bugwarrior` looks through the directories in
``$XDG_CONFIG_DIRS`` for a configuration file named
``bugwarrior/bugwarriorrc``.
The directories in ``$XDG_CONFIG_DIRS`` should be separated with a colon ':'.
If ``$XDG_CONFIG_DIRS`` is either not set or empty, a value equal to
``/etc/xdg`` is used.
