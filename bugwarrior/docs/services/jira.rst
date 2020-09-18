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

.. note::

   The `jira.password` may contain an `api token <https://confluence.atlassian.com/cloud/api-tokens-938839638.html>`_.

The above example is the minimum required to import issues from
Jira.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`
or described in `Service Features`_ below.

Service Features
----------------

The following default configuration is used::

    jira.import_labels_as_tags = False
    jira.import_sprints_as_tags = False
    jira.label_template = {{label}}
    jira.query = assignee = <jira.username> AND resolution is null
    jira.verify_ssl = True
    jira.version = 5


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

Do Not Verify SSL Certificate
+++++++++++++++++++++++++++++

If you want to ignore verifying the SSL certificate, set::

    jira.verify_ssl = False

Import Labels and Sprints as Tags
+++++++++++++++++++++++++++++++++

The Jira issue tracker allows you to attach labels to issues; to
use those labels as tags, you can use the ``jira.import_labels_as_tags``
option::

    jira.import_labels_as_tags = True

You can also import the names of any sprints associated with an issue as tags,
by setting the ``jira.import_sprints_as_tags`` option::

    jira.import_sprints_as_tags = True

If you would like to control how these labels are created, you can specify a
template used for converting the Jira label into a Taskwarrior tag.

For example, to prefix all incoming labels with the string 'jira_' (perhaps
to differentiate them from any existing tags you might have), you could
add the following configuration option::

    jira.label_template = jira_{{label}}

In addition to the context variable ``{{label}}``, you also have access
to all fields on the Taskwarrior task if needed.

.. note::

   See :ref:`field_templates` for more details regarding how templates
   are processed.

Kerberos authentication
+++++++++++++++++++++++

If the ``password`` is specified as ``@kerberos``, the service plugin will try
to authenticate against server with kerberos. A ticket must be already present
on the client (created by running ``kinit`` or any other method).


Cookie auth vs. HTTP-Basic auth
+++++++++++++++++++++++++++++++

If the ``use_cookies`` option is set to ``True``, the credentials are used for
Cookie-based authentication as opposed to HTTP-Basic authenticaton. This only
makes sense when Kerberos is not being used (see above).

This is useful in situations where HTTP-Basic auth is disabled or disallowed
for some reason.

When using API token
++++++++++++++++++++

Some hosts only support API tokens to authenticate. If so, ``bugwarrior-pull`` will respond with ``Err: 401 Unauthorized``. Create a token here_. Handle the token like it is a password.

.. _here: https://id.atlassian.com/manage-profile/security/api-tokens


Provided UDA Fields
-------------------

+---------------------+--------------------------------+---------------------+
| Field Name          | Description                    | Type                |
+=====================+================================+=====================+
| ``jiradescription`` | Description                    | Text (string)       |
+---------------------+--------------------------------+---------------------+
| ``jiraid``          | Issue ID                       | Text (string)       |
+---------------------+--------------------------------+---------------------+
| ``jirasummary``     | Summary                        | Text (string)       |
+---------------------+--------------------------------+---------------------+
| ``jiraurl``         | URL                            | Text (string)       |
+---------------------+--------------------------------+---------------------+
| ``jiraestimate``    | Estimate                       | Decimal (numeric)   |
+---------------------+--------------------------------+---------------------+
| ``jirasubtasks``    | ,-separated subtasks Issue IDs | Text (string)       |
+---------------------+--------------------------------+---------------------+
