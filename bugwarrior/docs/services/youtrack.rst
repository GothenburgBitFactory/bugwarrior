YouTrack
========

You can import tasks from your YouTrack instance using
the ``youtrack`` service name.

Example Service
---------------

Here's an example of a YouTrack target::

    [my_issue_tracker]
    service = youtrack
    youtrack.host = youtrack.example.com
    youtrack.login = turing
    youtrack.password = 3n1Gm@

The above example is the minimum required to import issues from
YouTrack.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`
or described in `Service Features`_ below.

Service Features
----------------

Customize the YouTrack Connection
+++++++++++++++++++++++++++++++++

The ``youtrack.host`` field is used to construct a URL for
the YouTrack server. It defaults to a secure connection scheme (HTTPS)
on the standard port (443).

To connect on a different port, set::

    youtrack.port = 8443

If your YouTrack instance is only available over HTTP, set::

    youtrack.use_https = False

If you want to ignore verifying the SSL certificate, set::

    youtrack.verify_ssl = False

For YouTrack InCloud instances set::

    youtrack.incloud_instance = True

Specify the Query to Use for Gathering Issues
+++++++++++++++++++++++++++++++++++++++++++++

The default option selects unresolved issues assigned to the login user::

    youtrack.query = for:me #Unresolved

Reference the
`YouTrack Search Query Grammar <https://www.jetbrains.com/help/youtrack/standalone/7.0/Search-Query-Grammar.html>`_
for additional examples.

Queries are capped at 100 max results by default, but may be adjusted to meet your needs::

    youtrack.query_limit = 100

Import Issue Tags
+++++++++++++++++

The YouTrack issue tracker allows you to tag issues. To apply these tags in Taskwarrior, set::

    youtrack.import_tags = True

If you would like to control how these tags are formatted, you can
specify a template used for converting the YouTrack tag into a Taskwarrior
tag.

For example, to prefix all incoming tags with the string 'yt\_' (perhaps
to differentiate them from any existing tags you might have), you could
add the following configuration option::

    youtrack.tag_template = yt_{{tag|lower}}

In addition to the context variable ``{{tag}}``, you also have access
to all fields on the Taskwarrior task if needed.

.. note::

   See :ref:`field_templates` for more details regarding how templates
   are processed.

Provided UDA Fields
-------------------

+---------------------------+----------------------+---------------------+
| Field Name                | Description          | Type                |
+===========================+======================+=====================+
| ``youtrackissue``         | PROJECT-ISSUE#       | Text (string)       |
+---------------------------+----------------------+---------------------+
| ``youtracksummary``       | Summary              | Text (string)       |
+---------------------------+----------------------+---------------------+
| ``youtrackurl``           | URL                  | Text (string)       |
+---------------------------+----------------------+---------------------+
| ``youtrackproject``       | Project short name   | Text (string)       |
+---------------------------+----------------------+---------------------+
| ``youtracknumber``        | Project issue number | Numeric             |
+---------------------------+----------------------+---------------------+
