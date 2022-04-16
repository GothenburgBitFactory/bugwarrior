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
    redmine.project_name = redmine
    redmine.issue_limit = 100

You can also feel free to use any of the configuration options described in
:ref:`common_configuration_options`.

There are also `redmine.login`/`redmine.password` settings if your
instance is behind basic auth.

If you want to ignore verifying the SSL certificate, set::

    redmine.verify_ssl = False

Specify the parameters to filter issues
+++++++++++++++++++++++++++++++++++++++

If you want a finer control over the filtering of issues, you may combine
`service.only_if_assigned` and `service.issue_limit` with the `redmine.query`
setting.

    redmine.query = project_id=10&status_id=15

Note that no `&` or `?` character is needed at the beginning of the setting
value.

You may find documentation about the redmine issue api
`on this page <https://www.redmine.org/projects/redmine/wiki/Rest_Issues>`_:

Provided UDA Fields
-------------------

+---------------------------+--------------------+--------------------+
| Field Name                | Description        | Type               |
+===========================+====================+====================+
| ``redmineid``             | ID                 | Text (string)      |
+---------------------------+--------------------+--------------------+
| ``redminesubject``        | Subject            | Text (string)      |
+---------------------------+--------------------+--------------------+
| ``redmineurl``            | URL                | Text (string)      |
+---------------------------+--------------------+--------------------+
| ``redminedescription``    | Description        | Text (string)      |
+---------------------------+--------------------+--------------------+
| ``redminetracker``        | Tracker            | Text (string)      |
+---------------------------+--------------------+--------------------+
| ``redminestatus``         | Status             | Text (string)      |
+---------------------------+--------------------+--------------------+
| ``redmineauthor``         | Author             | Text (string)      |
+---------------------------+--------------------+--------------------+
| ``redminecategory``       | Category           | Text (string)      |
+---------------------------+--------------------+--------------------+
| ``redminestartdate``      | Start Date         | Date               |
+---------------------------+--------------------+--------------------+
| ``redminespenthours``     | Spent Hours        | Duration           |
+---------------------------+--------------------+--------------------+
| ``redmineestimatedhours`` | Estimated Hours    | Duration           |
+---------------------------+--------------------+--------------------+
| ``redminecreatedon``      | Created On         | Date               |
+---------------------------+--------------------+--------------------+
| ``redmineupdatedon``      | Updated On         | Date               |
+---------------------------+--------------------+--------------------+
| ``redmineduedate``        | Due Date           | Date               |
+---------------------------+--------------------+--------------------+
| ``redmineassignedto``     | Assigned To        | Text (string)      |
+---------------------------+--------------------+--------------------+
| ``redmineprojectname``    | Project            | Text (string)      |
+---------------------------+--------------------+--------------------+
