Jitamin
=======

You can import tasks from your Jitamin instance using
the ``jitamin`` service name.

Example Service
---------------

Here's an example of a Jitamin target::

    [my_issue_tracker]
    service = jitamin
    jitamin.username = ralphbean
    jitamin.password = OMG_LULZ
    jitamin.base_uri = https://jitamin.com

The above example is the minimum required to import tasks from
Jitamin.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`
or described in `Service Features`_ below.

Service Features
----------------

Use Column as tag
+++++++++++++++++

If you want the column of the task to be a tag, you can do this with::

    jitamin.column_as_tag = True

Custom query strings
++++++++++++++++++++

By default, jitamin will search for all open tasks.

You may override this query string through your `bugwarriorrc` file.

For example::

    jitamin.query = assignee:me project:"My project"


Do Not Verify SSL Certificate
+++++++++++++++++++++++++++++

If you want to ignore verifying the SSL certificate, set::

    jitamin.verify_ssl = False

Provided UDA Fields
-------------------

.. udas:: bugwarrior.services.jitamin.JitaminIssue
