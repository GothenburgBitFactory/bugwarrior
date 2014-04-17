Redmine
=======

You can import tasks from your Redmine instance using
the ``redmine`` service name.

Example Service
---------------

Here's an example of an Redmine target::

    [my_issue_tracker]
    service = redmine
    redmine.url = http://redmine.example.org/
    redmine.key = c0c4c014cafebabe
    redmine.user_id = 7
    redmine.project_name = redmine

The above example is the minimum required to import issues from
Redmine.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`.

Provided UDA Fields
-------------------

+--------------------+--------------------+--------------------+
| Field Name         | Description        | Type               |
+====================+====================+====================+
| ``redmineid``      | ID                 | Text (string)      |
+--------------------+--------------------+--------------------+
| ``redminesubject`` | Subject            | Text (string)      |
+--------------------+--------------------+--------------------+
| ``redmineurl``     | URL                | Text (string)      |
+--------------------+--------------------+--------------------+
