Phabricator
===========

You can import tasks from your Phabricator instance using
the ``phabricator`` service name.

Example Service
---------------

Here's an example of an Phabricator target::

    [my_issue_tracker]
    service = phabricator

.. note::

   Although this may not look like enough information for us
   to gather information from Phabricator, 
   but credentials will be gathered from the user's ``~/.arcrc``.

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
