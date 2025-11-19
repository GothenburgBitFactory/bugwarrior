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

- the value of $BUGWARRIORRC if set
- $XDG_CONFIG_HOME/bugwarrior/bugwarriorrc if exists
- $XDG_CONFIG_HOME/bugwarrior/bugwarrior.toml if exists
- ~/.bugwarriorrc if exists
- ~/.bugwarrior.toml if exists
- <dir>/bugwarrior/bugwarriorrc if exists, for dir in $XDG_CONFIG_DIRS
- <dir>/bugwarrior/bugwarrior.toml if exists, for dir in $XDG_CONFIG_DIRS
- $XDG_CONFIG_HOME/bugwarrior/bugwarriorrc otherwise

See Also
--------

https://bugwarrior.readthedocs.io
