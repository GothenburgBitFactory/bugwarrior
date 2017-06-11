Phabricator
===========

You can import tasks from your Phabricator instance using
the ``phabricator`` service name.

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

The above example is the minimum required to import issues from
Phabricator.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`.

Service Features
----------------

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

Import Projects as Tags
+++++++++++++++++++++++

Phabricator tasks may belong to multiple projects, and differentials (PRs)
belong to a diffusion repository which may belong to multiple projects; to
use those projects' slugs (short identifying, human readable strings) as
tags, you can use the ``phabricator.should_set_tags`` option::

    phabricator.should_set_tags = True

If you are unhappy with the Phabricator slugs, you can supply a series
of substitutions to apply to them. You can do this using a list of
regexes and replacement strings. A '#' character separates the regex and
the replacement string, and you may supply as many of these modifiers as
you like by separating them with commas. They are applied in order. Use
the ``phabricator.tag_substitutions`` option::

    phabricator.tag_substitutions = infrastructure#infra,platform_mobile_apps#m

Here you can see that I replace 'infrastructure' with 'infra', and the
overly long 'platform_mobile_apps' slug with 'm'.

You can also specify a template used for converting the project slug
into a Taskwarrior tag. Templating happens after any substitutions.

For example, to prefix all incoming labels with the string 'phab_' (perhaps
to differentiate them from any existing tags you might have), you could
add the following configuration option::

    phabricator.tag_template = phab_{{project_slug}}

In addition to the context variable ``{{project_slug}}``, you also have
access to all fields on the Taskwarrior task if needed.

After all other processing, tags are normalized to ensure they work with
TaskWarrior. Any non-latin, non-alphanumeric character is turned into
underscore.

.. note::

   See :ref:`field_templates` for more details regarding how templates
   are processed.


Provided UDA Fields
-------------------

+----------------------+----------------------+----------------------+
| Field Name           | Description          | Type                 |
+======================+======================+======================+
| ``phabricatorid``    | Object               | Text (string)        |
+----------------------+----------------------+----------------------+
| ``phabricatortitle`` | Title                | Text (string)        |
+----------------------+----------------------+----------------------+
| ``phabricatortype``  | Type                 | Text (string)        |
+----------------------+----------------------+----------------------+
| ``phabricatorurl``   | URL                  | Text (string)        |
+----------------------+----------------------+----------------------+
