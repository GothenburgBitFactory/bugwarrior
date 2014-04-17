Bitbucket
=========

You can import tasks from your Bitbucket instance using
the ``bitbucket`` service name.

Example Service
---------------

Here's an example of an Bitbucket target::

    [my_issue_tracker]
    service = bitbucket
    bitbucket.username = ralphbean
    bitbucket.password = mypassword

The above example is the minimum required to import issues from
Bitbucket.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`.

Provided UDA Fields
-------------------

+--------------------+--------------------+--------------------+
| Field Name         | Description        | Type               |
+====================+====================+====================+
| ``bitbucketid``    | Issue ID           | Text (string)      |
+--------------------+--------------------+--------------------+
| ``bitbuckettitle`` | Title              | Text (string)      |
+--------------------+--------------------+--------------------+
| ``bitbucketurl``   | URL                | Text (string)      |
+--------------------+--------------------+--------------------+
