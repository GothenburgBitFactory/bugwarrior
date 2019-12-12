Pivotal Tracker
===============

You can import tasks from your Pivotal Tracker account using
the ``pivotaltracker`` service name.


Example Service
---------------

Here's an example of a Pivotal Tracker target::

    [my_issue_tracker]
    service = pivotaltracker
    pivotaltracker.user_d = 123456
    pivotaltracker.account_ids = 123456
    pivotaltracker.token = <your account API token>

The above example is the minimum required to import stories from
Pivotal Tracker.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`
or described in `Service Features`_ below.

.. describe:: pivotaltracker.user_id

    Your Pivotal Tracker user account.

    You can get your user_id by going to https://www.pivotaltracker.com/services/v5/me. It's the id field in the JSON response.

.. describe:: pivotaltracker.token

    Pivotal Tracker offers API keys for accounts to access resources through their
    API. You will need to provide ``pivotaltracker.token`` to allow bugwarrior to
    pull stories.

.. describe:: pivotaltracker.account_ids

    Pivotal Tracker account ids to specify which accounts to pull stories.

.. describe:: pivotaltracker.version

    Pivotal Tracker api version to access. The options are ``v5`` and ``edge``.
    Default is ``v5``.

.. describe:: pivotaltracker.host

    Pivotal Tracker host, default is ``https://www.pivotaltracker.com/services``.

.. describe:: pivotaltracker.excude_projects

    The list of projects to exclude. If omitted, bugwarrior will use all projects
    the authenticated user is a member of. This must be the projects id, In your browser,
    navigate to the project you want to pull stories from and look at the URL,
    it should be something like https://www.pivotaltracker.com/n/projects/xxxxxxxx:
    copy the part after /b/projects/ in the pivotaltracker.exclude_projects field.

.. describe:: pivotaltracker.excude_stories

    The list of stories to exclude. If omitted, bugwarrior will use all stories
    the authenticated user is assigned to. This must be the story id and Pivotal
    Tracker provides an easy way to get that id. Navigate in your browser to the
    story you wish to exlcude and copy the id next to 'ID' in the story. *Do not
    include the #*

.. describe:: pivotaltracker.excude_tags

    If set, pull all stories except for stories with those tags listed.

.. describe:: pivotaltracker.import_blockers

    A boolean that indicates whether to include blockers when listed in a story.

.. describe:: pivotaltracker.blocker_template

   Template used to convert Pivotal Trcker story blockers to a template defined
   before being pushed to UDA.
   See :ref:`field_templates` for more details regarding how templates
   are processed.
   The default value is ``Description: {{description}} State: {{resolved}}\n``.

.. describe:: pivotaltracker.import_labels_as_tags

    A boolean that indicates whether the Pivotal Tracker labels should be imported as
    tags in taskwarrior. (Defaults to false.)

.. describe:: pivotaltracker.label_template

   Template used to convert Pivotal Tracker labels to taskwarrior tags.
   See :ref:`field_templates` for more details regarding how templates
   are processed.
   The default value is ``{{label|replace(' ', '_')}}``.

.. describe:: pivotaltracker.annotation_template

   Template used to convert Pivotal Tracker story tasks to a template defined
   before being added as task annotations.
   See :ref:`field_templates` for more details regarding how templates
   are processed.
   The default value is ``status: {{complete}} - {{description}}``.

   .. note::

      Using ``annotations_templates`` will break so do not use it.


Service Features
----------------

Exclude Certain Projects
++++++++++++++++++++++++

If you happen to be working with a large number of projects, you
may want to pull stories from only a subset of your projects.  To
do that, you can use the ``pivotaltracker.exclude_projects`` option.

For example, if you have a particularly noisy project, you can
instead choose to import all stories except for the project listed
using the ``pivotaltracker.exclude_projects`` configuration option.

In this example, ``noisy_project`` is the project you would
*not* like stories created for::

    pivotaltracker.exclude_projects = noisy_project

Exclude Certain Stories
+++++++++++++++++++++++

If you want bugwarrior to not track specific stories you can ignore those
stories and ensure bugwarrior only tracks the stories you want. To do
this, you need to set::

    pivotaltracker.exclude_stories = 123456

For example, if you have stories #123 and #344, you do not wish to pull anymore
you can add them like so::

    pivotaltracker.exclude_stories = 123,344

Import Labels as Tags
+++++++++++++++++++++

Pivotal Tracker allows you to attach labels to stories; to
use those labels as tags, you can use the
``pivotaltracker.import_labels_as_tags`` option::

    pivotaltracker.import_labels_as_tags = True

Also, if you would like to control how these labels are created, you can
specify a template used for converting the Pivotal Tracker label into a
Taskwarrior tag.

For example, to prefix all incoming labels with the string `pivotal_` (perhaps
to differentiate them from any existing tags you might have), you could
add the following configuration option::

    pivotaltracker.label_template = pivotal_{{label}}

In addition to the context variable ``{{label}}``, you also have access
to all fields on the Taskwarrior task, if needed.

.. note::

   See :ref:`field_templates` for more details regarding how templates
   are processed.

Get involved stories
++++++++++++++++++++

By default, stories from all projects assigned to ``pivotaltracker.user_id``
are tracked. To turn this off, set::

    pivotaltracker.only_if_assigned = False

Instead of fetching stories on ``pivotaltracker.user_id``'s assigned
stories, you may instead get those that are not assigned to
``pivotaltracker.user_id``. This includes all stories in all projects
the user has access to. To pull stories, use::

    pivotaltracker.also_unassigned = True

To only pull stories where ``{{user_id}}`` is the requestor of the story, use::

    pivotaltracker.only_if_author = True


Queries
+++++++

Pivotal Traker provides a decent search feature in their API. If you want
to write your own query, as described at
https://www.pivotaltracker.com/help/articles/advanced_search/ you will need to use::

    pivotaltracker.query = mywork:1234

.. note::
   Search is limited by project and will be used in each
   project to determine what is pulled.

To disable the pre-defined query described above and synchronize only the
issues matched by a query, set::

   pivotaltracker.query = <Your customer query>

.. note::
   Setting a custom query will pull everything that is returned from the result.
   Be sure you are aware of what your query is doing before having burwarrior
   pull.


Story Tasks
+++++++++++

Pivotal Tracker provides the ability to add tasks to stories. Stories pulled in
by bugwarrior will create an annotation for each "subtask" provided in the
story. To turn this off, set::

    pivotaltracker.annotation_comments = False

Also, if you would like to control how these blockers are created, you can
specify a template used for converting the story blocker into a more reasonable
format.

For example, the default template::

   Completed: {{complete}} - {{description}}

Which will result in the following output::

   Completed: False - Do a thing and get rewarded.

add the following configuration option::

    pivotaltracker.annotation_template = {{description}} #{{id}} S{{complete}}

In addition to the context variable listed above, you also have access
to all fields on the Taskwarrior task and all fields of the blocking object as
shown here https://www.pivotaltracker.com/help/api/rest/v5#Story_Tasks.


Story Blocker
+++++++++++++

Pivotal Tracker allows you assign blockers to stories. To include blockers in
the stories pulled by bugwarrior, set::

    pivotaltracker.import_blockers = True

Also, if you would like to control how these blockers are created, you can
specify a template used for converting the story blocker into a more reasonable
format.

For example, the default template::

   Description: {{description}} Resolved: {{resolved}}\n

Which will result in the following output::

   Description: You cant do this stoy yet! Resovled: False

add the following configuration option::

    pivotaltracker.blocker_template = {{description}} #{{id}} S{{resolved}}

In addition to the context variable listed above, you also have access
to all fields on the Taskwarrior task and all fields of the blocking object as
shown here https://www.pivotaltracker.com/help/api/rest/v5#Blockers.


Provided UDA Fields
-------------------

+----------------------------+-------------------+-----------------+
| Field Name                 | Description       | Type            |
+============================+===================+=================+
| ``pivotaldescription``     | Story Description | Text (string)   |
+----------------------------+-------------------+-----------------+
| ``pivotalstorytype``       | Story Type        |  Text (string)  |
|                            |     (story, issue)|                 |
+----------------------------+-------------------+-----------------+
| ``pivotalrequesters``      | Story Requested By| Text (string)   |
+----------------------------+-------------------+-----------------+
| ``pivotalid``              | Story ID          | Numeric         |
+----------------------------+-------------------+-----------------+
| ``pivotalestimate``        | Story Estimate    | Text (string)   |
+----------------------------+-------------------+-----------------+
| ``pivotalblockers``        | Story Blockers    | Text (string)   |
+----------------------------+-------------------+-----------------+
| ``pivotalcreated``         | Story Created     | Date (date)     |
+----------------------------+-------------------+-----------------+
| ``pivotalupdated``         | Story Updated     | Date (date)     |
+----------------------------+-------------------+-----------------+
| ``pivotalclosed``          | Story Closed      | Date (date)     |
+----------------------------+-------------------+-----------------+