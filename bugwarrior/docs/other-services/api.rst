Python API v2.0
===============

The interfaces documented here are considered stable. All other interfaces
should be considered private to bugwarrior and are subject to change without
warning, release notes, or semantic version bumping.

.. automodule:: bugwarrior.services
   :members:
   :exclude-members: __init__,model_config
   :member-order: bysource

.. automodule:: bugwarrior.config
   :members:
   :exclude-members: __init__,compute_templates,model_config
   :imported-members:
   :member-order: bysource

Changelog
---------

v2.0
~~~~

- Removed ``Service.get_keyring_service(config)``. Service configurations should
  define ``KEYRING_SERVICE`` instead.
- Added ``ServiceConfig.KEYRING_SERVICE`` as a format string for generating the
  keyring service identifier from service configuration fields.
