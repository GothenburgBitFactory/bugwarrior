Trello
======

You can import tasks from Trello using the ``trello`` service name.

Example Service
---------------

Here's an example of a Trello target::

    [my_project]
    service = trello
    trello.api_key = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    trello.token = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

The above example is the minimum required to import tasks from Trello.  This
will import every card from all your bord as a separate task.  Feel free to use
any of the configuration options described in
:ref:`common_configuration_options` or described in `Service Features`_ below.

.. HINT:
   Getting your API key and access token

   To get your API key, go to https://trello.com/app-key and copy the given
   key (this is your ``trello.api_key``). Next, go to
   https://trello.com/1/connect?key=TRELLO_API_KEY&name=bugwarrior&response_type=token&scope=read,write&expiration=never
   replacing ``TRELLO_API_KEY`` by the key you got on the last step. Copy the
   given toke (this is your ``trello.token``).

Service Features
----------------

Include and Exclude Certain Boards
++++++++++++++++++++++++++++++++++

If you have many boards, you
may want to pull cards from only a subset of them.  To
do that, you can use the ``trello.boards`` option.

For example, if you would like to only pull-in issues from
your ``Work`` and ``My project`` boards, you could add
this line to your service configuration::

    trello.boards = Work,My project


Import Labels as Tags
+++++++++++++++++++++

Trello allows you to attach labels to cards; to use those labels as tags, you
can use the ``trello.import_labels_as_tags`` option::

    trello.import_labels_as_tags = True

Also, if you would like to control how these labels are created, you can
specify a template used for converting the gitlab label into a Taskwarrior
tag.

For example, to prefix all incoming labels with the string 'gitlab_' (perhaps
to differentiate them from any existing tags you might have), you could
add the following configuration option::

    gitlab.label_template = gitlab_{{label}}

In addition to the context variable ``{{label}}``, you also have access
to all fields on the Taskwarrior task if needed.

.. note::

   See :ref:`field_templates` for more details regarding how templates
   are processed.

Provided UDA Fields
-------------------

+-----------------------+-----------------------+---------------------+
| Field Name            | Description           | Type                |
+=======================+=======================+=====================+
| ``trelloboard``       | Board name            | Text (string)       |
+-----------------------+-----------------------+---------------------+
| ``trellocardid``      | Card ID               | Text (string)       |
+-----------------------+-----------------------+---------------------+
| ``trellodescription`` | Description           | Text (string)       |
+-----------------------+-----------------------+---------------------+
| ``trellotitle``       | Title                 | Text (string)       |
+-----------------------+-----------------------+---------------------+
| ``trellourl``         | URL                   | Text (string)       |
+-----------------------+-----------------------+---------------------+
