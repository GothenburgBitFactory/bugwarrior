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

Priority mapping
++++++++++++++++

Todoist task priorities ``p1``, ``p2``, and ``p3`` are mapped to the taskwarrior priorities
``H``, ``M``, and ``L`` respectively and ``p4`` leaves the priorty unset. 

Due and Deadline Date Mappings
++++++++++++++++++++++++++++++

By default the Todoist task due date is mapped to the taskwarrior ``due`` date field unless the Todiost task 
also has a deadline date set, in which case the tasks due date is mapped to ``scheduled`` and the deadline 
date is mappped to the taskwarrior ``due`` field.

Two alternative date mapping options are available by setting the ``due_date_mapping`` configuraiton option.

.. config::
    :fragment: todoist

    todoist.due_date_mapping = always_scheduled

``always_due`` - always map the Todoist due date to the taskwarrior due date, and ignore the Deadline date.

``always_scheduled`` - always map the Todoist due date to taskwarrior scheduled date, and map deadline to due 
if deadline if set.

``default`` - map Todoist due date to taskwarrior due date unless deadline is set, as descripbed above.

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

For example, to prefix all incoming labels with the string 'todoist_' (perhaps
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
