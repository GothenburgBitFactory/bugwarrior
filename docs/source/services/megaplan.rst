Megaplan
========

You can import tasks from your Megaplan instance using
the ``megaplan`` service name.

Example Service
---------------

Here's an example of an Megaplan target::

    [my_issue_tracker]
    service = megaplan
    megaplan.hostname = example.megaplan.ru
    megaplan.login = alice
    megaplan.password = secret
    megaplan.project_name = example

Provided UDA Fields
-------------------

+-------------------+-------------------+-------------------+
| Field Name        | Description       | Type              |
+===================+===================+===================+
| ``megaplanid``    | Issue ID          | Text (string)     |
+-------------------+-------------------+-------------------+
| ``megaplantitle`` | Title             | Text (string)     |
+-------------------+-------------------+-------------------+
| ``megaplanurl``   | URL               | Text (string)     |
+-------------------+-------------------+-------------------+
