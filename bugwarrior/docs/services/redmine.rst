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

.. udas:: bugwarrior.services.redmine.RedMineIssue
