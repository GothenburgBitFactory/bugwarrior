Kanboard
========

You can import tasks from your Kanboard instance using the ``kanboard`` service name.

Additional Requirements
-----------------------

Install the following package using ``pip``:

* ``kanboard``

Example Service
---------------

Here's an example of a Kanboard project::

    [my_issue_tracker]
    service = "kanboard"
    url = "https://kanboard.example.org"
    username = "ralph"
    password = "my_api_token"

The above example is the minimum required to import issues from Kanboard. It is
recommended to use a personal API token instead of a password, which can be
created on the Kanboard settings page. You can also feel free to use any of the
configuration options described in `Service Features`_ below.

Service Features
----------------

Specify the Query to Use for Gathering Issues
+++++++++++++++++++++++++++++++++++++++++++++

By default, all open issues assigned to the specified username are imported.
One may use the `query` parameter to modify the search query.

For example, to import all open issues assigned to 'frank', use the following
configuration option::

    query = "status:open assignee:frank"


Provided UDA Fields
-------------------

.. udas:: bugwarrior.services.kanboard.KanboardIssue
