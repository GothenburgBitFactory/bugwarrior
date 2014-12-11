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

The above example is the minimum required to import issues from
Bugzilla.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`.
Note, however, that the filtering options, including ``only_if_assigned``
and ``also_unassigned``, do not work

There is an option to ignore bugs that you are only cc'd on::

    bugzilla.ignore_cc = True

But this will continue to include bugs that you reported, regardless of
whether they are assigned to you.

If the filtering options are not sufficient to find the set of bugs you'd like,
you can tell Bugwarrior exactly which bugs to sync by pasting a full query URL
from your browser into the ``bugzilla.query_url`` option::

    bugzilla.query_url = https://bugzilla.mozilla.org/query.cgi?bug_status=ASSIGNED&email1=myname%40mozilla.com&emailassigned_to1=1&emailtype1=exact

Provided UDA Fields
-------------------

+---------------------+---------------------+---------------------+
| Field Name          | Description         | Type                |
+=====================+=====================+=====================+
| ``bugzillasummary`` | Summary             | Text (string)       |
+---------------------+---------------------+---------------------+
| ``bugzillaurl``     | URL                 | Text (string)       |
+---------------------+---------------------+---------------------+
| ``bugzillabugid``   | Bug ID              | Numeric (integer)   |
+---------------------+---------------------+---------------------+
