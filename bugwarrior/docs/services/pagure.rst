Pagure
======

You can import tasks from your private or public `pagure <https://pagure.io>`_
instance using the ``pagure`` service name.

Example Service
---------------

Here's an example of a Pagure target::

    [my_issue_tracker]
    service = pagure
    pagure.tag = releng
    pagure.base_url = https://pagure.io

The above example is the minimum required to import issues from
Pagure.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`
or described in `Service Features`_ below.

Note that **either** ``pagure.tag`` or ``pagure.repo`` is required.

- ``pagure.tag`` offers a flexible way to import issues from many pagure repos.
  It will include issues from *every* repo on the pagure instance that is
  *tagged* with the specified tag.  It is similar in usage to a github
  "organization".  In the example above, the entry will pull issues from all
  "releng" pagure repos.
- ``pagure.repo`` offers a simple way to import issues from a single pagure repo.

Note -- no authentication tokens are needed to pull issues from pagure.

Service Features
----------------

Include and Exclude Certain Repositories
++++++++++++++++++++++++++++++++++++++++

If you happen to be working with a large number of projects, you
may want to pull issues from only a subset of your repositories.  To 
do that, you can use the ``pagure.include_repos`` option.

For example, if you would like to only pull-in issues from
your ``project_foo`` and ``project_fox`` repositories, you could add
this line to your service configuration::

    pagure.tag = fedora-infra
    pagure.include_repos = project_foo,project_fox

Alternatively, if you have a particularly noisy repository, you can
instead choose to import all issues excepting it using the
``pagure.exclude_repos`` configuration option.  

In this example, ``noisy_repository`` is the repository you would
*not* like issues created for::

    pagure.tag = fedora-infra
    pagure.exclude_repos = noisy_repository

Import Labels as Tags
+++++++++++++++++++++

The Pagure issue tracker allows you to attach tags to issues; to
use those pagure tags as taskwarrior tags, you can use the
``pagure.import_tags`` option::

    pagure.import_tags = True

Also, if you would like to control how these taskwarrior tags are created, you
can specify a template used for converting the Pagure tag into a Taskwarrior
tag.

For example, to prefix all incoming labels with the string 'pagure_' (perhaps
to differentiate them from any existing tags you might have), you could
add the following configuration option::

    pagure.label_template = pagure_{{label}}

In addition to the context variable ``{{label}}``, you also have access
to all fields on the Taskwarrior task if needed.

.. note::

   See :ref:`field_templates` for more details regarding how templates
   are processed.

Provided UDA Fields
-------------------

+-----------------------+---------------------+---------------------+
| Field Name            | Description         | Type                |
+=======================+=====================+=====================+
| ``paguredatecreated`` | Created             | Date & Time         |
+-----------------------+---------------------+---------------------+
| ``pagurenumber``      | Issue/PR #          | Numeric             |
+-----------------------+---------------------+---------------------+
| ``paguretitle``       | Title               | Text (string)       |
+-----------------------+---------------------+---------------------+
| ``paguretype``        | Type                | Text (string)       |
+-----------------------+---------------------+---------------------+
| ``pagureurl``         | URL                 | Text (string)       |
+-----------------------+---------------------+---------------------+
| ``pagurerepo``        | username/reponame   | Text (string)       |
+-----------------------+---------------------+---------------------+
