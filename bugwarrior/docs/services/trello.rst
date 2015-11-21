Trello
======

You can import tasks from Trello cards using the ``trello`` service name.

Example Service
---------------

Here's an example of a Trello target::

    [my_project]
    service = trello
    trello.api_key = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    trello.token = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    trello.board = AaBbCcDd

The above example is the minimum required to import tasks from Trello.  This
will import every card from the specified board.  The value for
``trello.board`` can be either the board id of the board "short link".  The
later is the easiest option as it is part of the board URL: in your browser,
navigate to the board you want to pull cards from and look at the URL, it
should be something like ``https://trello.com/b/xxxxxxxx/myboard``: copy the
part between ``/b/`` and the next ``/`` in the ``trello.board`` field.

Feel free to use any of the configuration options described in
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

Include and Exclude Certain Lists
+++++++++++++++++++++++++++++++++

You may want to pull cards from only a subset of the open lists in your board.
To do that, you can use the ``trello.include_lists`` and
``trello.exclude_lists`` options.

For example, if you would like to only pull-in cards from
your ``To do`` and ``Doing`` lists, you could add this line to your service
configuration::

    trello.include_lists = To do, Doing


Import Labels as Tags
+++++++++++++++++++++

Trello allows you to attach labels to cards; to use those labels as tags, you
can use the ``trello.import_labels_as_tags`` option::

    trello.import_labels_as_tags = True

Also, if you would like to control how these labels are created, you can
specify a template used for converting the trello label into a Taskwarrior
tag.

For example, to prefix all incoming labels with the string 'trello_' (perhaps
to differentiate them from any existing tags you might have), you could
add the following configuration option::

    trello.label_template = trello_{{label}}

In addition to the context variable ``{{label}}``, you also have access
to all fields on the Taskwarrior task if needed.

.. note::

   See :ref:`field_templates` for more details regarding how templates
   are processed.  The default value is ``{{label|upper|replace(' ', '_')}}``.

Provided UDA Fields
-------------------

+-----------------------+-----------------------+---------------------+
| Field Name            | Description           | Type                |
+=======================+=======================+=====================+
| ``trelloboard``       | Board name            | Text (string)       |
+-----------------------+-----------------------+---------------------+
| ``trellocard``        | Card name             | Text (string)       |
+-----------------------+-----------------------+---------------------+
| ``trellocardid``      | Card ID               | Text (string)       |
+-----------------------+-----------------------+---------------------+
| ``trellolist``        | List name             | Text (string)       |
+-----------------------+-----------------------+---------------------+
| ``trelloshortlink``   | Short Link            | Text (string)       |
+-----------------------+-----------------------+---------------------+
| ``trelloshorturl``    | Short URL             | Text (string)       |
+-----------------------+-----------------------+---------------------+
| ``trellourl``         | Full URL              | Text (string)       |
+-----------------------+-----------------------+---------------------+
