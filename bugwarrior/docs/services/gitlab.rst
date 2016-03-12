Gitlab
======

You can import tasks from your Gitlab instance using
the ``gitlab`` service name.

Example Service
---------------

Here's an example of a Gitlab target::

    [my_issue_tracker]
    service = gitlab
    gitlab.login = ralphbean
    gitlab.token = OMG_LULZ
    gitlab.host = gitlab.com

The above example is the minimum required to import issues from
Gitlab.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`
or described in `Service Features`_ below.

The ``gitlab.token`` is your private API token.

Service Features
----------------

Include and Exclude Certain Repositories
++++++++++++++++++++++++++++++++++++++++

If you happen to be working with a large number of projects, you
may want to pull issues from only a subset of your repositories.  To
do that, you can use the ``gitlab.include_repos`` option.

For example, if you would like to only pull-in issues from
your ``project_foo`` and ``project_fox`` repositories, you could add
this line to your service configuration::

    gitlab.include_repos = project_foo,project_fox

Alternatively, if you have a particularly noisy repository, you can
instead choose to import all issues excepting it using the
``gitlab.exclude_repos`` configuration option.

In this example, ``noisy_repository`` is the repository you would
*not* like issues created for::

    gitlab.exclude_repos = noisy_repository

Import Labels as Tags
+++++++++++++++++++++

The gitlab issue tracker allows you to attach labels to issues; to
use those labels as tags, you can use the ``gitlab.import_labels_as_tags``
option::

    gitlab.import_labels_as_tags = True

Also, if you would like to control how these labels are created, you can
specify a template used for converting the gitlab label into a Taskwarrior
tag.

For example, to prefix all incoming labels with the string 'gitlab_' (perhaps
to differentiate them from any existing tags you might have), you could
add the following configuration option::

    gitlab.label_template = gitlab_{{label}}

In addition to the context variable ``{{label}}``, you also have access
to all fields on the Taskwarrior task if needed.

.. note::

   See :ref:`field_templates` for more details regarding how templates
   are processed.

Include Merge Requests
++++++++++++++++++++++

Although you can filter issues using :ref:`common_configuration_options`,
merge requests are not filtered by default.  You can filter merge requests
by adding the following configuration option::

    gitlab.filter_merge_requests = True

Use HTTP
++++++++

If your Gitlab instance is only available over HTTP, set::

    gitlab.use_https = False

Do Not Verify SSL Certificate
+++++++++++++++++++++++++++++

If want to ignore verifying the SSL certificate, set::

    gitlab.verify_ssl = False


Provided UDA Fields
-------------------

+-----------------------+-----------------------+---------------------+
| Field Name            | Description           | Type                |
+=======================+=======================+=====================+
| ``gitlabdescription`` | Description           | Text (string)       |
+-----------------------+-----------------------+---------------------+
| ``gitlabcreatedon``   | Created               | Date & Time         |
+-----------------------+-----------------------+---------------------+
| ``gitlabmilestone``   | Milestone             | Text (string)       |
+-----------------------+-----------------------+---------------------+
| ``gitlabnumber``      | Issue/MR #            | Numeric             |
+-----------------------+-----------------------+---------------------+
| ``gitlabtitle``       | Title                 | Text (string)       |
+-----------------------+-----------------------+---------------------+
| ``gitlabtype``        | Type                  | Text (string)       |
+-----------------------+-----------------------+---------------------+
| ``gitlabupdatedat``   | Updated               | Date & Time         |
+-----------------------+-----------------------+---------------------+
| ``gitlaburl``         | URL                   | Text (string)       |
+-----------------------+-----------------------+---------------------+
| ``gitlabrepo``        | username/reponame     | Text (string)       |
+-----------------------+-----------------------+---------------------+
| ``gitlabupvotes``     | Number of upvotes     | Numeric             |
+-----------------------+-----------------------+---------------------+
| ``gitlabdownvotes``   | Number of downvotes   | Numeric             |
+-----------------------+-----------------------+---------------------+
| ``gitlabwip``         | Work-in-Progress flag | Numeric             |
+-----------------------+-----------------------+---------------------+
| ``gitlabauthor``      | Issue/MR author       | Text (string)       |
+-----------------------+-----------------------+---------------------+
| ``gitlabassignee``    | Issue/MR assignee     | Text (string)       |
+-----------------------+-----------------------+---------------------+
