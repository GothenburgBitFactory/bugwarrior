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
visit the Todoist `<developer console https://app.todoist.com/app/settings/integrations/developer>`,
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

Additionally the standard options ``only_if_assigned`` and ``also_unassigned`` can be set
to modify the filter. These effectively _and_ additional filters the default or user provider query filter

.. config::
    :fragment: todoist

    todoist.only_if_assigned = me
    todoist.also_unassigned = true

``only_if_assigned``: If set, only import issues from shared projects assigned to the specified user. 
User can be identified by their name, email address, or ``me``. Issues for personal (not shared) projects
are always imported. Equivilent to filer ``shared & assigned to: <value>``

``also_unassigned``: If set to ``true`` and ``only_if_assigned`` is set, then also create tasks
 for issues that are not assigned to anybody. This only applies the tasks in shared projects, 
 tasks in personal (not shared) projects will always be imported. Defaults to ``false``.
 Equivilent to filer ``!assigned``

Priority mapping
++++++++++++++++

Todoist task priorities ``p1``, ``p2``, and ``p3`` are mapped to the taskwarrior priorities
``H``, ``M``, and ``L`` respectively and ``p4`` leaves the priorty unset. 

Due and Deadline Date Mappings
++++++++++++++++++++++++++++++

By default the Todoist task due date is mapped to the taskwarrior ``due`` date field and Todoist deadline
dates are available as a UDA.

You can alter the date mapping using ``due_template`` and ``scheduled_template`` configuration options.
For example if you prefer to use due date for when to start working on a task for tasks that have a deadline
date set, as suggestion in the Todosit ``difference between a date and a deadline https://www.todoist.com/help/articles/introduction-to-deadlines-uMqbSLM6U#h_01JDS5KZG9AMRPBWBEK366TXGE``,
you can use the following templates.

.. config::
    :fragment: todoist

    todoist.due_template = {{ todoistdeadline if todoistdeadline else todoistdue if todoistdue else "" }}
    todoist.scheduled_template = {{ todoistdue if todoistdeadline else "" }}

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

Import Labels as Tags
+++++++++++++++++++++

Todoist allows you to attach `labels <https://www.todoist.com/help/articles/introduction-to-labels-dSo2eE>` 
to issues; to use those labels as tags, you can use the ``import_labels_as_tags`` option:

.. config::
    :fragment: todoist

    todoist.import_labels_as_tags = True

Also, if you would like to control how these labels are created, you can
specify a template used for converting the Todoist label into a Taskwarrior
tag.

For example, to prefix all incoming labels with the string 'todoist\_' (perhaps
to differentiate them from any existing tags you might have), you could
add the following configuration option:

.. config::
    :fragment: todoist
    
    todoist.label_template = todoist_{{label}}

In addition to the context variable ``{{label}}``, you also have access
to all fields on the Taskwarrior task if needed.

.. note::
   See :ref:`field_templates` for more details regarding how templates
   are processed.

Provided UDA Fields
-------------------

.. udas:: bugwarrior.services.todoist.TodoistIssue
