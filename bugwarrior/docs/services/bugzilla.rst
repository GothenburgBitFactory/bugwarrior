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
    service = "bugzilla"
    base_uri = "https://bugzilla.redhat.com"
    username = "rbean@redhat.com"
    password = "OMG_LULZ"

Alternately, if you are using a version of python-bugzilla newer than 2.1.0,
you can specify an API key instead of a password. Note that the username is
still required in this case, in order to identify bugs belonging to you.

::

    api_key = "4f4d475f4c554c5a4f4d475f4c554c5a"

The above example is the minimum required to import issues from
Bugzilla.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`.

There is also an option to ignore bugs that you are only cc'd on::

    ignore_cc = true

If your bugzilla "actionable" bugs only include ON_QA, FAILS_QA, PASSES_QA, and POST::

    open_statuses = ["ON_QA", "FAILS_QA", "PASSES_QA", "POST"]

This won't create tasks for bugs in other states. The default open statuses:
``[ "NEW", "ASSIGNED", "NEEDINFO", "ON_DEV", "MODIFIED", "POST", "REOPENED", "ON_QA", "FAILS_QA", "PASSES_QA"]``

If you're on a more recent Bugzilla install, the NEEDINFO status no longer
exists, and has been replaced by the "needinfo?" flag. Set
``include_needinfos`` to `true` to have taskwarrior also add bugs where
information is requested of you. The "bugzillaneedinfo" UDA will be filled in
with the date the needinfo was set.

To see all your needinfo bugs, you can use ``task bugzillaneedinfo.any: list``.

If the filtering options are not sufficient to find the set of bugs you'd like,
you can tell Bugwarrior exactly which bugs to sync by pasting a full query URL
from your browser into the ``query_url`` option::

    query_url = "https://bugzilla.mozilla.org/query.cgi?bug_status=ASSIGNED&email1=myname%40mozilla.com&emailassigned_to1=1&emailtype1=exact"

Note that versions of Python-Bugzilla newer than 2.3.0 support the Bugzilla REST interface, but prefer the XMLRPC interface if both are configured.
To force use of the REST interface, ensure you are using a newer version of the library and add::

    force_rest = true

More modern bugzilla's require that we specify query_format=advanced along with
the xmlrpc request (https://bugzilla.redhat.com/show_bug.cgi?id=825370)
…but older bugzilla's don't know anything about that argument. Here we make it
possible for the user to specify whether they want to pass that argument or not::

    advanced = true

Provided UDA Fields
-------------------

.. udas:: bugwarrior.services.bz.BugzillaIssue
