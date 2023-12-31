Command Line Interface
======================

.. click:: bugwarrior:pull
  :prog: bugwarrior pull
  :nested: full

.. click:: bugwarrior:uda
  :prog: bugwarrior uda
  :nested: full

.. click:: bugwarrior:vault
  :prog: bugwarrior vault
  :nested: full

.. _configuration-files:

Configuration files
-------------------

Bugwarrior will look at the following paths and read its configuration from the
first existing file in this order:

* :file:`~/.config/bugwarrior/bugwarriorrc`
* :file:`~/.bugwarriorrc`
* :file:`/etc/xdg/bugwarrior/bugwarriorrc`

The default paths can be altered using the environment variables below.


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

See Also
--------

https://bugwarrior.readthedocs.io
