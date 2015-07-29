Jira
====

You can import tasks from your Jira instance using
the ``jira`` service name.

Additional Requirements
-----------------------

Install the following package using ``pip``:

* ``jira``

Example Service
---------------

Here's an example of a jira project::

    [my_issue_tracker]
    service = jira
    jira.base_uri = https://bug.tasktools.org
    jira.username = ralph
    jira.password = OMG_LULZ

.. note::

   The ``base_uri`` must not have a trailing slash.

The above example is the minimum required to import issues from
Jira.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`
or described in `Service Features`_ below.

Service Features
----------------

Specify the Query to Use for Gathering Issues
+++++++++++++++++++++++++++++++++++++++++++++

By default, the JIRA plugin will include any issues that are assigned to you
but do not yet have a resolution set, but you can fine-tune the query used
for gathering issues by setting the ``jira.query`` parameter.

For example, to select issues assigned to 'ralph' having a status that is
not 'closed' and is not 'resolved', you could add the following
configuration option::

    jira.query = assignee = ralph and status != closed and status != resolved

This query needs to be modified accordingly to the literal values of your Jira
instance; if the name contains any character, just put it in quotes, e.g.

    jira.query = assignee = 'firstname.lastname' and status != Closed and status != Resolved and status != Done

Jira v4 Support
+++++++++++++++

If you happen to be using a very old version of Jira, add the following
configuration option to your service configuration::

    jira.version = 4

Disabling SSL Verification
++++++++++++++++++++++++++

If your Jira instance is only available over HTTPS, and you're running into
``SSL: CERTIFICATE_VERIFY_FAILED``, it's possible to disable SSL verification::

    jira.verify_ssl = False

Import Labels as Tags
+++++++++++++++++++++

The Jira issue tracker allows you to attach labels to issues; to
use those labels as tags, you can use the ``jira.import_labels_as_tags``
option::

    jira.import_labels_as_tags = True

Also, if you would like to control how these labels are created, you can
specify a template used for converting the Jira label into a Taskwarrior
tag.

For example, to prefix all incoming labels with the string 'jira_' (perhaps
to differentiate them from any existing tags you might have), you could
add the following configuration option::

    jira.label_template = jira_{{label}}

In addition to the context variable ``{{label}}``, you also have access
to all fields on the Taskwarrior task if needed.

.. note::

   See :ref:`field_templates` for more details regarding how templates
   are processed.

Provided UDA Fields
-------------------

+---------------------+---------------------+---------------------+
| Field Name          | Description         | Type                |
+=====================+=====================+=====================+
| ``jiradescription`` | Description         | Text (string)       |
+---------------------+---------------------+---------------------+
| ``jiraid``          | Issue ID            | Text (string)       |
+---------------------+---------------------+---------------------+
| ``jirasummary``     | Summary             | Text (string)       |
+---------------------+---------------------+---------------------+
| ``jiraurl``         | URL                 | Text (string)       |
+---------------------+---------------------+---------------------+
| ``jiraestimate``    | Estimate            | Decimal (numeric)   |
+---------------------+---------------------+---------------------+
