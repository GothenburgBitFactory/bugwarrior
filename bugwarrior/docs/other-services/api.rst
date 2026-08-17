Python API v2.0
===============

The interfaces documented here are considered stable. All other interfaces
should be considered private to bugwarrior and are subject to change without
warning, release notes, or semantic version bumping.

.. automodule:: bugwarrior.services
   :members:
   :exclude-members: __init__,model_config
   :member-order: bysource

.. automodule:: bugwarrior.task
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

- Added the ``bugwarrior.task`` module, holding the ``Task`` and ``Udas`` models
  a service maps its records onto.
- Changed ``Issue.to_taskwarrior()`` to return a ``Task`` rather than a
  dictionary.
- Removed ``Issue.UDAS`` and ``Issue.UNIQUE_KEY``. A service now declares each
  UDA as a field of a ``Udas`` subclass, whose ``UNIQUE_KEY`` names the fields
  identifying a task. The UDA type is derived from the field's annotation and
  its label from the field's title.
- Added ``Service.TASK_SCHEMA``, naming the ``Task`` subclass a service maps to.
- Added ``Service.process_record(record, extra)``, which maps a record to a
  ``Task`` and applies the user's templates. ``Service.issues()`` now yields
  those tasks rather than ``Issue`` objects.
- Removed the type parameter from ``Service``. Subclasses declare
  ``class MyService(Service)`` rather than ``class MyService(Service[MyIssue])``.
- Removed ``Issue.parse_date(date)``. A date field accepts the service's raw
  string and parses it, adding UTC when the string carries no timezone. Use
  ``bugwarrior.task.coerce_datetime`` if you need the datetime before the task
  is built.
- Removed ``Service.get_keyring_service(config)``. Service configurations should
  define ``KEYRING_SERVICE`` instead.
- Added ``ServiceConfig.KEYRING_SERVICE`` as a format string for generating the
  keyring service identifier from service configuration fields.
- Added ``Issue.render_tags_from_labels(labels)`` for rendering taskwarrior tags
  from service labels with ``label_template``.
