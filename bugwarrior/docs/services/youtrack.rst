YouTrack
========

You can import tasks from your YouTrack instance using
the ``youtrack`` service name.

Example Service
---------------

Here's an example of a YouTrack target::

    [my_issue_tracker]
    service = "youtrack"
    host = "youtrack.example.com"
    login = "turing"
    password = "3n1Gm@"

The above example is the minimum required to import issues from
YouTrack. You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`
or described in `Service Features`_ below.

Service Features
----------------

Unauthenticated
+++++++++++++++

While the ``login`` and ``password`` fields are still required, bugwarrior
will not log in to the service if you set::

    anonymous = true

.. note::

    This makes no attempt at IP obfuscation.

Customize the YouTrack Connection
+++++++++++++++++++++++++++++++++

The ``host`` field is used to construct a URL for
the YouTrack server. It defaults to a secure connection scheme (HTTPS)
on the standard port (443).

To connect on a different port, set::

    port = 8443

If your YouTrack instance is only available over HTTP, set::

    use_https = false

If you want to ignore verifying the SSL certificate, set::

    verify_ssl = false

For YouTrack InCloud instances set::

    incloud_instance = true

Specify the Query to Use for Gathering Issues
+++++++++++++++++++++++++++++++++++++++++++++

The default option selects unresolved issues assigned to the login user::

    query = "for:me #Unresolved"

Reference the
`YouTrack Search Query Grammar <https://www.jetbrains.com/help/youtrack/standalone/7.0/Search-Query-Grammar.html>`_
for additional examples.

Queries are capped at 100 max results by default, but may be adjusted to meet your needs::

    query_limit = 100

Import Issue Tags
+++++++++++++++++

The YouTrack issue tracker allows you to tag issues and these tags are applied
to tasks by default. To disable this behavior, set::

    import_tags = false

If you would like to control how these tags are formatted, you can
specify a template used for converting the YouTrack tag into a Taskwarrior
tag.

For example, to prefix all incoming tags with the string 'yt\_' (perhaps
to differentiate them from any existing tags you might have), you could
add the following configuration option::

    tag_template = "yt_{{tag|lower}}"

In addition to the context variable ``{{tag}}``, you also have access
to all fields on the Taskwarrior task if needed.

.. note::

   See :ref:`field_templates` for more details regarding how templates
   are processed.

Provided UDA Fields
-------------------

.. udas:: bugwarrior.services.youtrack.YoutrackIssue
