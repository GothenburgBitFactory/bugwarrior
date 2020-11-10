Bugzilla
=========================

You can import tasks from your Bz instance using
the ``bugzilla`` service name.

Additional Dependencies
-----------------------

Install packages needed for Bugzilla support with::

    pip install bugwarrior[bugzilla]

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

Alternately, if you are using a version of python-bugzilla newer than 2.1.0,
you can specify an API key instead of a password. Note that the username is
still required in this case, in order to identify bugs belonging to you.

::

    bugzilla.api_key = 4f4d475f4c554c5a4f4d475f4c554c5a

The above example is the minimum required to import issues from
Bugzilla.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`.

There is also an option to ignore bugs that you are only cc'd on::

    bugzilla.ignore_cc = True

If your bugzilla "actionable" bugs only include ON_QA, FAILS_QA, PASSES_QA, and POST::

    bugzilla.open_statuses = ON_QA,FAILS_QA,PASSES_QA,POST

This won't create tasks for bugs in other states. The default open statuses:
"NEW,ASSIGNED,NEEDINFO,ON_DEV,MODIFIED,POST,REOPENED,ON_QA,FAILS_QA,PASSES_QA"

If you're on a more recent Bugzilla install, the NEEDINFO status no longer
exists, and has been replaced by the "needinfo?" flag. Set
"bugzilla.include_needinfos" to "True" to have taskwarrior also add bugs where
information is requested of you. The "bugzillaneedinfo" UDA will be filled in
with the date the needinfo was set.

To see all your needinfo bugs, you can use "task bugzillaneedinfo.any: list".

If the filtering options are not sufficient to find the set of bugs you'd like,
you can tell Bugwarrior exactly which bugs to sync by pasting a full query URL
from your browser into the ``bugzilla.query_url`` option::

    bugzilla.query_url = https://bugzilla.mozilla.org/query.cgi?bug_status=ASSIGNED&email1=myname%40mozilla.com&emailassigned_to1=1&emailtype1=exact

Note that versions of Python-Bugzilla newer than 2.3.0 support the Bugzilla REST interface, but prefer the XMLRPC interface if both are configured.
To force use of the REST interface, ensure you are using a newer version of the library and add::

    bugzilla.force_rest = True

Provided UDA Fields
-------------------

+------------------------+-------------------------------+---------------------+
| Field Name             | Description                   | Type                |
+========================+===============================+=====================+
| ``bugzillasummary``    | Summary                       | Text (string)       |
+------------------------+-------------------------------+---------------------+
| ``bugzillaurl``        | URL                           | Text (string)       |
+------------------------+-------------------------------+---------------------+
| ``bugzillabugid``      | Bug ID                        | Numeric (integer)   |
+------------------------+-------------------------------+---------------------+
| ``bugzillastatus``     | Bugzilla Status               | Text (string)       |
+------------------------+-------------------------------+---------------------+
| ``bugzillaneedinfo``   | Needinfo                      | Date                |
+------------------------+-------------------------------+---------------------+
| ``bugzillaassignedon`` | date BZ was set to 'assigned' | Date                |
+------------------------+-------------------------------+---------------------+
