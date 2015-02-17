Phabricator
===========

You can import tasks from your Phabricator instance using
the ``phabricator`` service name.

Additional Requirements
-----------------------

Install the following package using ``pip``:

* ``phabricator``

Example Service
---------------

Here's an example of an Phabricator target::

    [my_issue_tracker]
    service = phabricator

.. note::

   Although this may not look like enough information for us
   to gather information from Phabricator, 
   but credentials will be gathered from the user's ``~/.arcrc``.

The above example is the minimum required to import issues from
Phabricator.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`.

Provided UDA Fields
-------------------

+----------------------+----------------------+----------------------+
| Field Name           | Description          | Type                 |
+======================+======================+======================+
| ``phabricatorid``    | Object               | Text (string)        |
+----------------------+----------------------+----------------------+
| ``phabricatortitle`` | Title                | Text (string)        |
+----------------------+----------------------+----------------------+
| ``phabricatortype``  | Type                 | Text (string)        |
+----------------------+----------------------+----------------------+
| ``phabricatorurl``   | URL                  | Text (string)        |
+----------------------+----------------------+----------------------+
