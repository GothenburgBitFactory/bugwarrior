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
    service = "versionone"
    base_uri = "https://www3.v1host.com/MyVersionOneInstance/"
    usermame = "somebody"
    password = "hunter5"

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
'Sprint 2014-09-22' -- by using the ``timebox_name`` option;
for example::

    timebox_name = "Sprint 2014-09-22"

Set a Global Project Name
+++++++++++++++++++++++++

By default, this importer does not set a project name on imported tasks.
Although you can gain more flexibility by using :ref:`field_templates`
to generate a project name, if all you need is to set a predictable
project name, you can use the ``project_name`` option; in this
example, to add imported tasks to the project 'important_project'::

    project_name = "important_project"

Set the Timezone Used for Due Dates
+++++++++++++++++++++++++++++++++++

You can configure the timezone used for setting your tasks' due dates
by setting the ``timezone`` option.  By default, your local
timezone will be used.  For example::

    timezone = "America/Los_Angeles"

Provided UDA Fields
-------------------

.. udas:: bugwarrior.services.versionone.VersionOneIssue
