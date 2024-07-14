Todoist
=======

You can import tasks from `Todoist <https://todoist.com/>`_ using
the ``todoist`` service name.

Example Service
---------------

Here is an example of a configuration for the ``todoist`` service:

.. config::

    [my_tasks]
    service = todoist
    todoist.token = <API_TOKEN>

The above example is the minimum required to import issues from
Todoist.  You can also use any of the
configuration options described in :ref:`common_configuration_options`
or described in `Service Features`_ below.

``token`` is required to authenticate with your Todoist account. To get the token, 
visit https://app.todoist.com/app/settings/integrations/developer.

Service Features
----------------

Filter tasks
++++++++++++

The ``filter`` option allows you to filter the tasks that are imported from Todoist.
By default the service has a blank filter which will import all active tasks. You
can use any `supported filter <https://todoist.com/help/articles/introduction-to-filters-V98wIH>`.
Multiple filters (using the comma , operator) are not supported.

.. config::
    :fragment: todoist

    todoist.filter = (today | tomorrow | overdue)


Provided UDA Fields
-------------------

.. udas:: bugwarrior.services.todoist.TodoistIssue
