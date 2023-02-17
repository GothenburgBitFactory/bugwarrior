Github
======

You can import tasks from your Github instance using
the ``github`` service name.

Example Service
---------------

Here's an example of a Github target::

    [my_issue_tracker]
    service = "github"
    login = "ralphbean"
    token = "123456"
    username = "ralphbean"

The above example is the minimum required to import issues from
Github.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`
or described in `Service Features`_ below.

``login`` is used to specify what account bugwarrior should use to login
to github, combined with ``token``.

To get a token, go to the "Personal access tokens" section of
your profile settings. Only the ``public_repo`` scope is required, but access
to private repos can be gained with ``repo`` as well.

Service Features
----------------

Repo Owner
++++++++++

``username`` indicates which repositories should be scraped.  For
instance, I always have ``login`` set to ralphbean (my account).  But I
have some targets with ``username`` pointed at organizations or other
users to watch issues there.  This parameter is required unless
``query`` is provided.

Include and Exclude Certain Repositories
++++++++++++++++++++++++++++++++++++++++

By default, issues from all repos belonging to ``username`` are
included. To turn this off, set::

    include_user_repos = false

If you happen to be working with a large number of projects, you
may want to pull issues from only a subset of your repositories.  To
do that, you can use the ``include_repos`` option.

For example, if you would like to only pull-in issues from
``some_user/project_foo`` and ``some_user/project_fox`` repositories, you could add
these lines to your service configuration::

    username = "some_user"
    include_repos = ["project_foo", "project_fox"]

Alternatively, if you have a particularly noisy repository, you can
instead choose to import all issues excepting it using the
``exclude_repos`` configuration option.

In this example, ``some_user/noisy_repository`` is the repository you would
*not* like issues created for::

    username = "some_user"
    exclude_repos = ["noisy_repository"]

Import Labels as Tags
+++++++++++++++++++++

The Github issue tracker allows you to attach labels to issues; to
use those labels as tags, you can use the ``import_labels_as_tags``
option::

    import_labels_as_tags = true

Also, if you would like to control how these labels are created, you can
specify a template used for converting the Github label into a Taskwarrior
tag.

For example, to prefix all incoming labels with the string 'github_' (perhaps
to differentiate them from any existing tags you might have), you could
add the following configuration option::

    label_template = "github_{{label}}"

In addition to the context variable ``{{label}}``, you also have access
to all fields on the Taskwarrior task if needed.

.. note::

   See :ref:`field_templates` for more details regarding how templates
   are processed.

Filter Pull Requests
++++++++++++++++++++

Although you can filter issues using :ref:`common_configuration_options`,
pull requests are not filtered by default.  You can filter pull requests
by adding the following configuration option::

    filter_pull_requests = true

Exclude Pull Requests
+++++++++++++++++++++

If you want bugwarrior to not track pull requests you can disable it altogether
and ensure bugwarrior only tracks issues::

    exclude_pull_requests = true

Get involved issues
+++++++++++++++++++

By default, bugwarrior pulls all issues across owned and member repositories
assigned to the authenticated user.  To disable this behavior, use::

    include_user_issues = false

Instead of fetching issues and pull requests based on ``{{username}}``'s owned
repositories, you may instead get those that ``{{username}}`` is involved in.
This includes all issues and pull requests where the user is the author, the
assignee, mentioned in, or has commented on.  To do so, add the following
configuration option::

    involved_issues = true

Queries
+++++++

If you want to write your own github query, as described at https://help.github.com/articles/searching-issues/::

    query = "assignee:octocat is:open"

Note that this search covers both issues and pull requests, which github treats
as a special kind of issue.

To disable the pre-defined queries described above and synchronize only the
issues matched by the query, set::

    include_user_issues = false
    include_user_repos = false

GitHub Enterprise Instance
++++++++++++++++++++++++++

If you're using GitHub Enterprise, the on-premises version of GitHub, you can
point bugwarrior to it with the ``host`` configuration option. E.g.::

    host = "github.acme.biz"

Synchronizing Issue Content
+++++++++++++++++++++++++++

This service synchronizes most GitHub fields to UDAs, as described below.
Comments are synchronized as annotations.

To limit the amount of content synchronized into TaskWarrior (which can help to avoid issues with synchronization), use

 * ``annotation_comments=false`` (a global configuration) to disable synchronizing comments to annotations; and
 * either ``body_length`` to limit the size of the Github Body UDA or include ``githubbody`` in ``static_fields`` in the ``[general]`` section to eliminate the UDA entirely.

Including Project Owner in Project Name
+++++++++++++++++++++++++++++++++++++++

By default the taskwarrior ``project`` name will not include the owner. To do so set::

    project_owner_prefix = true


Get Specific Issues
+++++++++++++++++++

Specific issues can be pulled in using ``issue_urls``::

    issue_urls = ["https://github.com/ralphbean/bugwarrior/issues/516", "https://github.com/ralphbean/bugwarrior/pull/898"]


Provided UDA Fields
-------------------

.. udas:: bugwarrior.services.github.GithubIssue
