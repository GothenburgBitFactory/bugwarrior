Nextcloud Deck
==============

You can import tasks from your Nextcloud Deck instance using the ``deck`` service name.

This service requires `deck <https://github.com/nextcloud/deck#installationupdate>`_ to be installed in a Nextcloud installation and available to bugwarrior.

Example Service
---------------

Here's an example of a Nextcloud Deck target::

   [my_nextcloud_deck]
   service = deck
   deck.base_uri = https://nextcloud.example.com
   deck.username = my_user
   deck.password = my-nextcloud-app-password

The above example is the minimum required to import issues from Deck.  You can also feel free to use any of the configuration options described in :ref:`common_configuration_options` or described in `Service Features`_ below.

The ``base_uri`` should point to the location of your Nextcloud installation.
``username`` should be the username of the user that has access to the Deck boards you are interested in.
``password`` should be an app-password (or the real password, although that is not recommended) of the user.

Service Features
----------------

Import Labels as Tags
+++++++++++++++++++++

The Deck allows you to attach labels to cards. To use those labels as tags, you can use the ``deck.import_labels_as_tags`` option::

    deck.import_labels_as_tags = True

Also, if you would like to control how these labels are created, you can specify a template used for converting the Deck label into a Taskwarrior tag.

For example, to prefix all incoming labels with the string 'deck\_' (perhaps to differentiate them from any existing tags you might have), you could add the following configuration option::

    deck.label_template = deck_{{label}}

In addition to the context variable ``{{label}}``, you also have access
to all fields on the Taskwarrior task if needed.

.. note::

   See :ref:`field_templates` for more details regarding how templates
   are processed.

Only if assigned
++++++++++++++++

You can filter for cards assigned to a specific user::

    deck.only_if_assigned = my_user

.. note::
    ``only_if_assigned`` can be set to a username, then only issues assigned to that user will be taken into account. Attention, deck can assign multiple users, and this plugin has no support for multiple assignees - it will always only take the first assignee into account.

Exclude / include board IDs
+++++++++++++++++++++++++++

You can explicitly exclude or include specific boards::

    deck.exclude_board_ids = 5,6
    deck.include_board_ids = 4

.. note::
    ``include_board_ids`` can explicitly include specific boards from importing;
    ``exclude_board_ids`` can explicitly exclude specific boards from importing.
    Use them to filter what cards you want to have imported.
    If both are defined, ``include_board_ids`` will be used.

Provided UDA Fields
-------------------

.. udas:: bugwarrior.services.deck.NextcloudDeckIssue
