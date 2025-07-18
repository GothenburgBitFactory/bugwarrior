Todoist
=======

You can import tasks from `Todoist <https://todoist.com/>`_ using
the ``todoist`` service name.

Example Service
---------------

Here is an example of a configuration for the ``todoist`` service:

.. config::

    [todoist]
    service = todoist
    todoist.token = <API_TOKEN>

The above example is the minimum required to import issues from
Todoist.  You can also use any of the
configuration options described in :ref:`common_configuration_options`
or described in `Service Features`_ below.

``token`` is required to authenticate with your Todoist account. To get the token 
visit the Todosit `<developer console https://app.todoist.com/app/settings/integrations/developer>`,
or see the Todoist documentition on how to `find your API token <https://www.todoist.com/help/articles/find-your-api-token-Jpzx9IIlB>`

Service Features
----------------

Task filters
++++++++++++

The ``filter`` option allows you to filter the tasks that are imported from Todoist.
By default the service has a blank filter which will import all active tasks. You
can use any `supported filter <https://todoist.com/help/articles/introduction-to-filters-V98wIH>`.
Multiple filters (using the comma , operator) are not supported.

.. config::
    :fragment: todoist

    todoist.filter = (today | tomorrow | overdue | next 5 days)

Priority mapping
++++++++++++++++

Todoist task priorities ``p1``, ``p2``, and ``p3`` are mapped to the taskwarrior priorities
``H``, ``M``, and ``L`` respectively.

Character replacement
+++++++++++++++++++++

This capability is in part to workaround ``ralphbean/taskw#172 <https://github.com/ralphbean/taskw/issues/172>``_
which causes the ``[`` and ``]`` characters to be over escaped as ``&open;`` and ``&close;``
when they are synced using bugwarrior.

To avoid display issues ``[`` and ``]`` are replaced by ``〈`` and ``〉`` in the Task title and description. 

You can override this default behaviour to use alternative custom characters by setting the ``char_*`` options.

.. config::
    :fragment: todoist

    todoist.char_open_bracket = (
    todoist.char_close_bracket = )

Lables
++++++

Todoist `Labels <https://www.todoist.com/help/articles/introduction-to-labels-dSo2eE>` are added as Taskwarrior tags.


Provided UDA Fields
-------------------

.. udas:: bugwarrior.services.todoist.TodoistIssue
