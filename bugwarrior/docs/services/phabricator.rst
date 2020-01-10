Phabricator
===========

You can import Maniphest tasks from your Phabricator instance using
the ``phabricator`` service name.

This service supports both Maniphest (Tasks) and Differential (Revision).

Additional Requirements
-----------------------

Install the following package using ``pip``:

* ``phabricator``

Example Service
---------------

Here's an example of a Phabricator target::

    [my_issue_tracker]
    service = phabricator

.. note::

   Although this may not look like enough information for us
   to gather information from Phabricator,
   but credentials will be gathered from the user's ``~/.arcrc``.

   To set up an ``~/.arcrc``, install arcanist and run ``arc
   install-certificate``

The above example is the minimum required to import issues from
Phabricator.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`.

Service Features
----------------

Filtering by User and Project
.............................

If you have dozens of users and projects, you might want to
pull the tasks and code review requests only for the specific ones.

If you want to show only the tasks related to a specific user,
you just need to add its PHID to the service configuration like this::

    phabricator.user_phids = PHID-USER-ab12c3defghi45jkl678

If you want to show only the tasks and diffs related to a specific project or a repository,
just add their PHIDs to the service configuration::

    phabricator.project_phids = PHID-PROJ-ab12c3defghi45jkl678,PHID-REPO-ab12c3defghi45jkl678

Both ``phabricator.user_phids`` and ``phabricator.project_phids`` accept
a comma-separated (no spaces) list of PHIDs.

If you specify both, you will get tasks and diffs that match one **or** the other.

When working on a Phabricator installations with a huge number of users or projects,
it is recommended that you specify ``phabricator.user_phids`` and/or ``phabricator.project_phids``,
as the Phabricator API may return a timeout for a query with too many results.

If you do not know PHID of a user, project or repository,
you can find it out by querying Phabricator Conduit
(``https://YOUR_PHABRICATOR_HOST/conduit/``) --
the methods which return the needed info are ``user.query``, ``project.query``
and ``repository.query`` respectively.

Selecting a Phabricator Host
............................

If your ``~/.arcrc`` includes credentials for multiple Phabricator instances,
it is undefined which one will be used. To make it explicit, you can use::

    phabricator.host = https://YOUR_PHABRICATOR_HOST

Where ``https://YOUR_PHABRICATOR_HOST`` **must match** the corresponding json key
in ``~/.arcrc``, which may include ``/api/`` besides your hostname.

Ignoring Some Items
...................

By default, any Task or Revision relating to any of the given users or projects
will be included.  This is likely more than you want!  You can ignore some user
relationships with the following configuration::

    phabricator.ignore_cc = True        # ignore CC field
    phabricator.ignore_author = True    # ignore Author field
    phabricator.ignore_owner = True     # ignore Owner field (Tasks only)
    phabricator.ignore_reviewers = True # ignore Reviewers field (Revisions only)

Note that there is no way to filter by the reviewer's response (for example, to
exclude Revisions you have already reviewed). Phabricator does not provide the
necessary information in the Conduit API.

Furthermore, setting `phabricator.only_if_assigned` to something other than False
will default to ignoring the CC and Author fields as reported in phabricator.

Provided UDA Fields
-------------------

+----------------------+--------------------------+----------------------+
| Field Name           | Description              | Type                 |
+======================+==========================+======================+
| ``phabricatorid``    | Object                   | Text (string)        |
+----------------------+--------------------------+----------------------+
| ``phabricatortitle`` | Title                    | Text (string)        |
+----------------------+--------------------------+----------------------+
| ``phabricatortype``  | Type (``issue`` for      | Text (string)        |
|                      | Tasks, ``pull_request``  |                      |
|                      | for Revisions)           |                      |
+----------------------+--------------------------+----------------------+
| ``phabricatorurl``   | URL                      | Text (string)        |
+----------------------+--------------------------+----------------------+
