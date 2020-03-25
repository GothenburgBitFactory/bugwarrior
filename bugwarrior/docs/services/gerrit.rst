Gerrit
======

You can import code reviews from a Gerrit instance using the ``gerrit`` service name.

Example Service
---------------

Here's an example of a gerrit project::

    [my_issue_tracker]
    service = gerrit
    gerrit.base_uri = https://yourhomebase.xyz/gerrit/
    gerrit.username = your_username
    gerrit.password = your_http_digest_password

The above example is the minimum required to import issues from Gerrit.

**Note** that the password is typically not your normal login password. Go to
the "HTTP Password" section in your account settings to generate/retrieve this
password.

You can also pass an optional ``gerrit.ssl_ca_path`` option which will use an
alternative certificate authority to verify the connection.

You can also feel free to use any of the configuration options described in
:ref:`common_configuration_options`.

Specify the Query to Use for Gathering Patchsets
++++++++++++++++++++++++++++++++++++++++++++++++

By default, the Gerrit plugin will query patchsets based on this simple
API query

    is:open+is:reviewer

You may override this query string through your `bugwarriorrc` file.

For example:

    gerrit.query = is:open+((reviewer:self+-owner:self+-is:ignored)+OR+assignee:self)

Provided UDA Fields
-------------------

+---------------------+---------------------+---------------------+
| Field Name          | Description         | Type                |
+=====================+=====================+=====================+
| ``gerritid``        | Issue ID            | Text (string)       |
+---------------------+---------------------+---------------------+
| ``gerritsummary``   | Summary             | Text (string)       |
+---------------------+---------------------+---------------------+
| ``gerriturl``       | URL                 | Text (string)       |
+---------------------+---------------------+---------------------+

The Gerrit service provides a limited set of UDAs.  If you have need for some
other values not present here, please file a request (there's lots of metadata
in there that we could expose).
