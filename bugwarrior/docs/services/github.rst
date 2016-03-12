Github
======

You can import tasks from your Github instance using
the ``github`` service name.

Example Service
---------------

Here's an example of a Github target::

    [my_issue_tracker]
    service = github
    github.username = ralphbean
    github.login = ralphbean
    github.password = OMG_LULZ

The above example is the minimum required to import issues from
Github.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`
or described in `Service Features`_ below.

Note that both ``github.username`` and ``github.login`` are required and can be
set to different values.  ``github.login`` is used to specify what account
bugwarrior should use to login to github.  ``github.username`` indicates which
repositories should be scraped.  For instance, I always have ``github.login``
set to ralphbean (my account).  But I have some targets with
``github.username`` pointed at organizations or other users to watch issues
there.

If two-factor authentication is used, ``github.token`` must be given rather
than ``github.password``. To get a token, go to the "Personal access tokens" section of
your profile settings. Only the ``public_repo`` scope is required, but access
to private repos can be gained with ``repo`` as well.

Service Features
----------------

Include and Exclude Certain Repositories
++++++++++++++++++++++++++++++++++++++++

If you happen to be working with a large number of projects, you
may want to pull issues from only a subset of your repositories.  To 
do that, you can use the ``github.include_repos`` option.

For example, if you would like to only pull-in issues from
your ``project_foo`` and ``project_fox`` repositories, you could add
this line to your service configuration::

    github.include_repos = project_foo,project_fox

Alternatively, if you have a particularly noisy repository, you can
instead choose to import all issues excepting it using the
``github.exclude_repos`` configuration option.  

In this example, ``noisy_repository`` is the repository you would
*not* like issues created for::

    github.exclude_repos = noisy_repository

Import Labels as Tags
+++++++++++++++++++++

The Github issue tracker allows you to attach labels to issues; to
use those labels as tags, you can use the ``github.import_labels_as_tags``
option::

    github.import_labels_as_tags = True

Also, if you would like to control how these labels are created, you can
specify a template used for converting the Github label into a Taskwarrior
tag.

For example, to prefix all incoming labels with the string 'github_' (perhaps
to differentiate them from any existing tags you might have), you could
add the following configuration option::

    github.label_template = github_{{label}}

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

    github.filter_pull_requests = True

Get involved issues
+++++++++++++++++++

Instead of fetching issues and pull requests based on ``{{username}}``'s owned
repositories, you may instead get those that ``{{username}}`` is involved in.
This includes all issues and pull requests where the user is the author, the
assignee, mentioned in, or has commented on.  To do so, add the following
configuration option::

    github.involved_issues = True

Provided UDA Fields
-------------------

+---------------------+---------------------+---------------------+
| Field Name          | Description         | Type                |
+=====================+=====================+=====================+
| ``githubbody``      | Body                | Text (string)       |
+---------------------+---------------------+---------------------+
| ``githubcreatedon`` | Created             | Date & Time         |
+---------------------+---------------------+---------------------+
| ``githubmilestone`` | Milestone           | Text (string)       |
+---------------------+---------------------+---------------------+
| ``githubnumber``    | Issue/PR #          | Numeric             |
+---------------------+---------------------+---------------------+
| ``githubtitle``     | Title               | Text (string)       |
+---------------------+---------------------+---------------------+
| ``githubtype``      | Type                | Text (string)       |
+---------------------+---------------------+---------------------+
| ``githubupdatedat`` | Updated             | Date & Time         |
+---------------------+---------------------+---------------------+
| ``githuburl``       | URL                 | Text (string)       |
+---------------------+---------------------+---------------------+
| ``githubrepo``      | username/reponame   | Text (string)       |
+---------------------+---------------------+---------------------+
