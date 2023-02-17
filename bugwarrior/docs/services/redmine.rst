Redmine
=======

You can import tasks from your Redmine instance using
the ``redmine`` service name.

Only first 100 issues are imported at the moment.

Example Service
---------------

Here's an example of a Redmine target::

    [my_issue_tracker]
    service = "redmine"
    url = "http://redmine.example.org/"
    key = "c0c4c014cafebabe"
    issue_limit = 100

You can also feel free to use any of the configuration options described in
:ref:`common_configuration_options`.

There are also `login`/`password` settings if your
instance is behind basic auth.

If you want to ignore verifying the SSL certificate, set::

    verify_ssl = false

Specify the parameters to filter issues
+++++++++++++++++++++++++++++++++++++++

If you want a finer control over the filtering of issues, you may combine
``only_if_assigned`` and ``issue_limit`` with the ``query`` setting::

    query = "project_id=10&status_id=15"

Note that no `&` or `?` character is needed at the beginning of the setting
value.

You may find documentation about the redmine issue api
`on this page <https://www.redmine.org/projects/redmine/wiki/Rest_Issues>`_:

Provided UDA Fields
-------------------

.. udas:: bugwarrior.services.redmine.RedMineIssue
