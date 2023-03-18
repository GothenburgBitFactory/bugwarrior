Gitlab
======

You can import tasks from your Gitlab instance using
the ``gitlab`` service name.

Example Service
---------------

Here's an example of a Gitlab target:

.. config::

    [my_issue_tracker]
    service = gitlab
    gitlab.login = ralphbean
    gitlab.token = OMG_LULZ
    gitlab.host = gitlab.com

The above example is the minimum required to import issues from
Gitlab.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`
or described in `Service Features`_ below.

The ``token`` is your private API token.

Service Features
----------------

Include and Exclude Certain Repositories
++++++++++++++++++++++++++++++++++++++++

If you happen to be working with a large number of projects, you
may want to pull issues from only a subset of your repositories.  To
do that, you can use the ``include_repos`` option.

For example, if you would like to only pull-in issues from
your own ``project_foo`` and team ``bar``'s ``project_fox`` repositories, you
could add this line to your service configuration (replacing ``me`` by your own
login):

.. config::
    :fragment: gitlab

    gitlab.include_repos = me/project_foo, bar/project_fox

Alternatively, if you have a particularly noisy repository, you can
instead choose to import all issues excepting it using the
``exclude_repos`` configuration option.

In this example, ``noisy/repository`` is the repository you would
*not* like issues created for:

.. config::
    :fragment: gitlab

    gitlab.exclude_repos = noisy/repository

.. hint::
   If you omit the repository's namespace, bugwarrior will automatically add
   your login as namespace. E.g. the following are equivalent:

.. config::
    :fragment: gitlab

    gitlab.login = foo
    gitlab.include_repos = bar

and:

.. config::
    :fragment: gitlab

    gitlab.login = foo
    gitlab.include_repos = foo/bar

Alternatively, you can use project IDs instead of names by prefixing the
project id with `id:`:

.. config::
    :fragment: gitlab

    gitlab.include_repos = id:1234,id:3141

Filtering Repositories with Regular Expressions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you don't want to list every single repository you want to include or
exclude, you can additionally use the options ``include_regex`` and
``exclude_regex`` and specify a regular expression (suitable for Python's
``re`` module).
No default namespace is applied here, the regular expressions are matched to the
full repository name with its namespace.

The regular expressions can be used in addition to the lists explained above.
So if a repository is not included in ``include_repos``, it can still be
included by ``include_regex``, and vice versa; and likewise for
``exclude_repos`` and ``exclude_regex``.

.. note::
   If a repository matches both the inclusion and the exclusion options, the
   exclusion takes precedence.

For example, you want to include only the repositories ``foo/node`` and
``bar/node`` as well as all repositories in the namespace ``foo`` starting with
``ep_``, but not ``foo/ep_example``:

.. config::
    :fragment: gitlab

    gitlab.include_repos = foo/node, bar/node
    gitlab.include_regex = foo/ep_.*
    gitlab.exclude_repos = foo/ep_example

Filtering Membership
^^^^^^^^^^^^^^^^^^^^

If you want to filter repositories that you have a membership:

.. config::
    :fragment: gitlab

    gitlab.membership = True

Filtering Owned
^^^^^^^^^^^^^^^^^^^^

If you want to filter repositories that you own:

.. config::
    :fragment: gitlab

    gitlab.owned = True

Import Labels as Tags
+++++++++++++++++++++

The gitlab issue tracker allows you to attach labels to issues; to
use those labels as tags, you can use the ``import_labels_as_tags``
option:

.. config::
    :fragment: gitlab

    gitlab.import_labels_as_tags = True

Also, if you would like to control how these labels are created, you can
specify a template used for converting the gitlab label into a Taskwarrior
tag.

For example, to prefix all incoming labels with the string 'gitlab_' (perhaps
to differentiate them from any existing tags you might have), you could
add the following configuration option:

.. config::
    :fragment: gitlab

    gitlab.label_template = gitlab_{{label}}

In addition to the context variable ``{{label}}``, you also have access
to all fields on the Taskwarrior task if needed:

.. note::

   See :ref:`field_templates` for more details regarding how templates
   are processed.

Include Issues
++++++++++++++

Issues are included by default, if not configured otherwise. To disable querying of issues, set:

.. config::
    :fragment: gitlab

    gitlab.include_issues = False

Include Merge Requests
++++++++++++++++++++++

Merge requests are included by default. You can exclude them by disabling
this feature:

.. config::
    :fragment: gitlab

    gitlab.include_merge_requests = False

Include Todo Items
++++++++++++++++++

By default todo items are not included.  You may include them by adding the
following configuration option:

.. config::
    :fragment: gitlab

    gitlab.include_todos = True

If todo items are included, by default, todo items for all projects are
included.  To apply the same repository filters to todos as to issues and merge requests, you
may set:

.. config::
    :fragment: gitlab

    gitlab.include_all_todos = False

Include Only One Author
+++++++++++++++++++++++

If you would like to only pull issues and MRs that you've authored, you may set:

.. config::
    :fragment: gitlab

    gitlab.only_if_author = myusername

Priority by type
++++++++++++++++

If you would like that your issues have a different default priority than your MRs or todo items,
you can configure individual priorities for each:

.. config::
    :fragment: gitlab

    gitlab.default_issue_priority = M
    gitlab.default_todo_priority = M
    gitlab.default_mr_priority = H


Custom query strings
++++++++++++++++++++

The Gitlab REST API allows many more configuration options than the ones provided
by the options explained above. If you want to further customize calls, you can set for example:

.. config::
    :fragment: gitlab

    gitlab.issue_query = issues?search=foo&in=title
    gitlab.merge_request_query = merge_requests?state=opened&scope=all&reviewer_username=myusername
    gitlab.todo_query = todos?state=pending&action=directly_addressed


These can be combined with the other configuration options above, but queries are only evaluated if
the respective category (issue, merge_request, todo) is enabled.

Note: Depending in the scope you are interested in, this query-based approach can be much faster
than using the "default queries". For example, imagine that you want to query all issues assigned
to your user.

This can be achieved by leaving the ``include_repos`` configuration value empty and
setting ``only_if_assigned`` to ``True``. This will result in querying all repos your user
has access to, which might take a very long time.

Alternatively, you could set ``issue_query =
issues?assignee_username=myusername&state=opened&scope=all``, which will fetch the assigned issues
first and then only fetch the projects for which issues have been found.

Use HTTP
++++++++

If your Gitlab instance is only available over HTTP, set:

.. config::
    :fragment: gitlab

    gitlab.use_https = False

Do Not Verify SSL Certificate
+++++++++++++++++++++++++++++

If you want to ignore verifying the SSL certificate, set:

.. config::
    :fragment: gitlab

    gitlab.verify_ssl = False

Including Project Owner in Project Name
+++++++++++++++++++++++++++++++++++++++

By default the taskwarrior ``project`` name will not include the owner. To do so set:

.. config::
    :fragment: gitlab

    gitlab.project_owner_prefix = True

Synchronizing Issue Content
+++++++++++++++++++++++++++

This service synchronizes most Gitlab fields to UDAs, as described below.

To limit the amount of content synchronized into TaskWarrior (which can help to avoid issues with synchronization), use

 * ``body_length=0`` to disable synchronizing the Gitlab Description UDA (or set it to a small value to limit size).

Provided UDA Fields
-------------------

.. udas:: bugwarrior.services.gitlab.GitlabIssue
