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
    service = "jira"
    base_uri = "https://bug.tasktools.org"
    username = "ralph"
    password = "8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903"

.. note::

   The ``base_uri`` must not have a trailing slash.

.. note::

   Basic authentication with passwords is deprecated. The `password` may contain an `api token <https://confluence.atlassian.com/cloud/api-tokens-938839638.html>`_ or alternatively you can set `PAT` to a Personal Access Token.

The above example is the minimum required to import issues from
Jira.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`
or described in `Service Features`_ below.

Service Features
----------------

The following default configuration is used::

    body_length = <sys.maxsize>
    import_labels_as_tags = false
    import_sprints_as_tags = false
    label_template = "{{label}}"
    query = "assignee = <jira.username> AND resolution is null"
    use_cookies = false
    verify_ssl = true
    version = 5


Specify the Query to Use for Gathering Issues
+++++++++++++++++++++++++++++++++++++++++++++

By default, the JIRA plugin will include any issues that are assigned to you
but do not yet have a resolution set, but you can fine-tune the query used
for gathering issues by setting the ``query`` parameter.

For example, to select issues assigned to 'ralph' having a status that is
not 'closed' and is not 'resolved', you could add the following
configuration option::

    query = "assignee = ralph and status != closed and status != resolved"

This query needs to be modified accordingly to the literal values of your Jira
instance; if the name contains any character, just put it in quotes, e.g.::

    query = "assignee = 'firstname.lastname' and status != Closed and status != Resolved and status != Done"

Jira v4 Support
+++++++++++++++

If you happen to be using a very old version of Jira, add the following
configuration option to your service configuration::

    version = 4

Do Not Verify SSL Certificate
+++++++++++++++++++++++++++++

If you want to ignore verifying the SSL certificate, set::

    verify_ssl = false

Import Labels and Sprints as Tags
+++++++++++++++++++++++++++++++++

The Jira issue tracker allows you to attach labels to issues; to
use those labels as tags, you can use the ``import_labels_as_tags``
option::

    import_labels_as_tags = true

You can also import the names of any sprints associated with an issue as tags,
by setting the ``import_sprints_as_tags`` option::

    import_sprints_as_tags = true

If you would like to control how these labels are created, you can specify a
template used for converting the Jira label into a Taskwarrior tag.

For example, to prefix all incoming labels with the string 'jira\_' (perhaps
to differentiate them from any existing tags you might have), you could
add the following configuration option::

    label_template = "jira_{{label}}"

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

If the ``use_cookies`` option is set to ``true``, the credentials are used for
Cookie-based authentication as opposed to HTTP-Basic authenticaton. This only
makes sense when Kerberos is not being used (see above).

This is useful in situations where HTTP-Basic auth is disabled or disallowed
for some reason.

Synchronizing Issue Content
+++++++++++++++++++++++++++

By default, this service synchronizes the description of the Jira issue as ``jiradescription``.
In some cases, this is not required.
It also risks triggering bugs in Taskwarrior around unicode encodings.

Set ``body_length`` to limit the size of the description UDA or include ``jiradescription`` in ``static_fields`` in the ``[general]`` section to eliminate the UDA entirely.

When using API token
++++++++++++++++++++

Some hosts only support API tokens to authenticate. If so, ``bugwarrior pull`` will respond with ``Err: 401 Unauthorized``. `Create a token`_. Handle the token like it is a password.

Note that if given a correct API token and an incorrect username, Jira will authenticate successfully but not allow access to any issues.

.. _Create a  token: https://id.atlassian.com/manage-profile/security/api-tokens

When using Personal Access Token
++++++++++++++++++++++++++++++++

Some hosts only support Personal Access Tokens (PATs) to authenticate. If so, ``bugwarrior pull`` will respond with ``Err: 401 Unauthorized``. Create a PAT as described `here`_.

Put the PAT in the ``PAT`` field and do not set ``password``.

.. _here: https://confluence.atlassian.com/enterprise/using-personal-access-tokens-1026032365.html


Provided UDA Fields
-------------------

.. udas:: bugwarrior.services.jira.JiraIssue

Support for Extra UDA Fields
+++++++++++++++++++++++++++++

To export additional UDA fields, set ``extra_fields`` to entries of the form ``uda_tag:field_key[.subkey]``. You can also chain subkeys to extract deeply embedded keys, e.g.::

    extra_fields = ["jiraextrafield1:customfield_10000", "jiraextrafield2:customfield_10001.attributes.description"]

The correct key (and subkeys) can be found by inspecting the `fields` attribute of a standard Jira issue response.
