Bugzilla
=========================

You can import tasks from your Bz instance using
the ``bugzilla`` service name.

Example Service
---------------

Here's an example of a bugzilla target.

This will scrape every ticket that:

1. Is not closed and
2. rbean@redhat.com is either the owner, reporter or is cc'd on the issue.
   
Bugzilla instances can be quite different from one another so use this
with caution and please report bugs so we can
make bugwarrior support more robust!

::

    [my_issue_tracker]
    service = bugzilla
    bugzilla.base_uri = bugzilla.redhat.com
    bugzilla.username = rbean@redhat.com
    bugzilla.password = OMG_LULZ

Provided UDA Fields
-------------------

+---------------------+---------------------+---------------------+
| Field Name          | Description         | Type                |
+=====================+=====================+=====================+
| ``bugzillasummary`` | Summary             | Text (string)       |
+---------------------+---------------------+---------------------+
| ``bugzillaurl``     | URL                 | Text (string)       |
+---------------------+---------------------+---------------------+
