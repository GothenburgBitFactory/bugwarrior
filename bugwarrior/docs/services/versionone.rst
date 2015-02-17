VersionOne
==========

You can import tasks from VersionOne using the ``versionone`` service name.

Additional Requirements
-----------------------

Install the following package using ``pip``:

* ``v1pysdk-unofficial``

Example Service
---------------

Here's an example of a VersionOne project::

    [my_issue_tracker]
    service = versionone
    versionone.base_uri = https://www3.v1host.com/MyVersionOneInstance/
    versionone.usermame = somebody
    versionone.password = hunter5

The above example is the minimum required to import issues from VersionOne.
You can also feel free to use any of the configuration options
described in :ref:`common_configuration_options`
or described in `Service Features`_ below.

.. note::

   This plugin does not infer a project name from any attribute of the
   version one Task or Story; it is recommended that you set the project
   name to use for imported tasks by either using the below
   `Set a Global Project Name`_ feature, or, if you require more
   flexibility, setting the ``project_template`` configuration
   option (see :ref:`field_templates`).

Service Features
----------------

Restrict Task Imports to a Specific Timebox (Sprint)
++++++++++++++++++++++++++++++++++++++++++++++++++++

You can restrict imported tasks to a specific Timebox (VersionOne's
internal generic name for a Sprint) -- in this example named
'Sprint 2014-09-22' -- by using the ``versionone.timebox_name`` option;
for example::

    versionone.timebox_name = Sprint 2014-09-22

Set a Global Project Name
+++++++++++++++++++++++++

By default, this importer does not set a project name on imported tasks.
Although you can gain more flexibility by using :ref:`field_templates`
to generate a project name, if all you need is to set a predictable
project name, you can use the ``versionone.project_name`` option; in this
example, to add imported tasks to the project 'important_project'::

    versionone.project_name = important_project

Set the Timezone Used for Due Dates
+++++++++++++++++++++++++++++++++++

You can configure the timezone used for setting your tasks' due dates
by setting the ``versionone.timezone`` option.  By default, your local
timezone will be used.  For example::

    versionone.timezone = America/Los_Angeles

Provided UDA Fields
-------------------

+-----------------------------------+-----------------------+---------------+
| Field Name                        | Description           | Type          |
+===================================+=======================+===============+
| ``versiononetaskname``            | Task Name             | Text (string) |
+-----------------------------------+-----------------------+---------------+
| ``versiononetaskoid``             | Task Object ID        | Text (string) |
+-----------------------------------+-----------------------+---------------+
| ``versiononestoryoid``            | Story Object ID       | Text (string) |
+-----------------------------------+-----------------------+---------------+
| ``versiononestoryname``           | Story Name            | Text (string) |
+-----------------------------------+-----------------------+---------------+
| ``versiononetaskreference``       | Task Reference        | Text (string) |
+-----------------------------------+-----------------------+---------------+
| ``versiononetaskdetailestimate``  | Task Detail Estimate  | Text (string) |
+-----------------------------------+-----------------------+---------------+
| ``versiononetaskestimate``        | Task Estimate         | Text (string) |
+-----------------------------------+-----------------------+---------------+
| ``versiononetaskdescrption``      | Task Description      | Text (string) |
+-----------------------------------+-----------------------+---------------+
| ``versiononetasktodo``            | Task To Do            | Text (string) |
+-----------------------------------+-----------------------+---------------+
| ``versiononestorydetailestimate`` | Story Detail Estimate | Text (string) |
+-----------------------------------+-----------------------+---------------+
| ``versiononestoryurl``            | Story URL             | Text (string) |
+-----------------------------------+-----------------------+---------------+
| ``versiononetaskurl``             | Task URL              | Text (string) |
+-----------------------------------+-----------------------+---------------+
| ``versiononestoryestimate``       | Story Estimate        | Text (string) |
+-----------------------------------+-----------------------+---------------+
| ``versiononestorynumber``         | Story Number          | Text (string) |
+-----------------------------------+-----------------------+---------------+
| ``versiononestorydescription``    | Story Description     | Text (string) |
+-----------------------------------+-----------------------+---------------+
