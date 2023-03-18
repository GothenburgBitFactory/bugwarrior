Trello
======

You can import tasks from Trello cards using the ``trello`` service name.


Options
-------

.. describe:: api_key

   Your Trello API key, available from https://trello.com/app-key.

.. describe:: token

   Your Trello token, available from https://trello.com/app-key.

   To get your token, click the link "Token" seen bellow:
       .. image:: pictures/trello_token.png

   Alternatively, go to
   https://trello.com/1/connect?key=TRELLO_API_KEY&name=bugwarrior&response_type=token&scope=read,write&expiration=never
   replacing ``TRELLO_API_KEY`` by the key you got on the last step.

.. describe:: include_boards

   The list of board to include. If omitted, bugwarrior will use all boards
   the authenticated user is a member of.
   This can be either the board ids of the board "short links".  The latter is
   the easiest option as it is part of the board URL: in your browser, navigate
   to the board you want to pull cards from and look at the URL, it should be
   something like ``https://trello.com/b/xxxxxxxx/myboard``: copy the part
   between ``/b/`` and the next ``/`` in the ``include_boards`` field.

   .. image:: pictures/trello_url.png
      :height: 1cm

.. describe:: include_lists

   If set, only pull cards from lists whose name is present in
   ``include_lists``.

.. describe:: exclude_lists

   If set, skip cards from lists whose name is present in
   ``exclude_lists``.

.. describe:: import_labels_as_tags

   A boolean that indicates whether the Trello labels should be imported as
   tags in taskwarrior. (Defaults to false.)

.. describe:: label_template

   Template used to convert Trello labels to taskwarrior tags.
   See :ref:`field_templates` for more details regarding how templates
   are processed.
   The default value is ``{{label|replace(' ', '_')}}``.

Example Service
---------------

Here's an example of a Trello target:

.. config::

    [my_project]
    service = trello
    trello.api_key = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    trello.token = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

The above example is the minimum required to import tasks from Trello.  This
will import every card from all the user's boards.

Here's an example with more options:

.. config::

    [my_project]
    service = trello
    trello.api_key = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    trello.token = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    trello.include_boards = AaBbCcDd, WwXxYyZz
    trello.include_lists = Todo, Doing
    trello.exclude_lists = Done
    trello.only_if_assigned = someuser
    trello.import_labels_as_tags = true

In this case, ``bugwarrior`` will only import cards from the specified boards
if they belong to the right lists..

Feel free to use any of the configuration options described in
:ref:`common_configuration_options` or described in `Service Features`_ below.


Service Features
----------------

Include and Exclude Certain Lists
+++++++++++++++++++++++++++++++++

You may want to pull cards from only a subset of the open lists in your board.
To do that, you can use the ``include_lists`` and
``exclude_lists`` options.

For example, if you would like to only pull-in cards from
your ``Todo`` and ``Doing`` lists, you could add this line to your service
configuration:

.. config::
    :fragment: trello

    trello.include_lists = Todo, Doing


Import Labels as Tags
+++++++++++++++++++++

Trello allows you to attach labels to cards; to use those labels as tags, you
can use the ``import_labels_as_tags`` option:

.. config::
    :fragment: trello

    trello.import_labels_as_tags = True

Also, if you would like to control how these labels are created, you can
specify a template used for converting the trello label into a Taskwarrior
tag.

For example, to prefix all incoming labels with the string 'trello_' (perhaps
to differentiate them from any existing tags you might have), you could
add the following configuration option:

.. config::
    :fragment: trello

    trello.label_template = trello_{{label}}

In addition to the context variable ``{{label}}``, you also have access
to all fields on the Taskwarrior task if needed.

.. note::

   See :ref:`field_templates` for more details regarding how templates
   are processed.  The default value is ``{{label|upper|replace(' ', '_')}}``.

Provided UDA Fields
-------------------

.. udas:: bugwarrior.services.trello.TrelloIssue
