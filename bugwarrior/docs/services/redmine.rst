Redmine
=======

You can import tasks from your Redmine instance using
the ``redmine`` service name.

Only first 100 issues are imported at the moment.

Example Service
---------------

Here's an example of a Redmine target::

    [my_issue_tracker]
    service = redmine
    redmine.url = http://redmine.example.org/
    redmine.key = c0c4c014cafebabe
    redmine.user_id = 7
    redmine.project_name = redmine
    redmine.issue_limit = 100

You can also feel free to use any of the configuration options described in
:ref:`common_configuration_options`.

There are also `redmine.login`/`redmine.password` settings if your
instance is behind basic auth.

If you want to ignore verifying the SSL certificate, set::

    redmine.verify_ssl = False

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
