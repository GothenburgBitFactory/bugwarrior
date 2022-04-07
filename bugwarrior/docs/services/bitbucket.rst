Bitbucket
=========

You can import tasks from your Bitbucket instance using
the ``bitbucket`` service name.

Example Service
---------------

Here's an example of a Bitbucket target::

    [my_issue_tracker]
    service = bitbucket
    bitbucket.username = ralphbean
    bitbucket.key = mykey
    bitbucket.secret = mysecret

The above example is the minimum required to import issues from
Bitbucket.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`.

To get a key and secret,
go to the "OAuth" section of your profile settings and click "Add consumer". Set the
"Callback URL" to ``https://localhost/`` and set the appropriate permissions. Then
assign your consumer's credentials to ``bitbucket.key`` and ``bitbucket.secret``.

Service Features
----------------

Include and Exclude Certain Repositories
++++++++++++++++++++++++++++++++++++++++

If you happen to be working with a large number of projects, you
may want to pull issues from only a subset of your repositories.  To
do that, you can use the ``bitbucket.include_repos`` option.

For example, if you would like to only pull-in issues from
your ``project_foo`` and ``project_fox`` repositories, you could add
this line to your service configuration::

    bitbucket.include_repos = project_foo,project_fox

Alternatively, if you have a particularly noisy repository, you can
instead choose to import all issues excepting it using the
``bitbucket.exclude_repos`` configuration option.

In this example, ``noisy_repository`` is the repository you would
*not* like issues created for::

    bitbucket.exclude_repos = noisy_repository

Please note that the API returns all lowercase names regardless of
the case of the repository in the web interface.

Include Merge Requests
++++++++++++++++++++++

Merge requests are included by default. You can exclude them by disabling
this feature::

    bitbucket.include_merge_requests = False

Project Owner Prefix
++++++++++++++++++++

To include the project owner in the project name::

    bitbucket.project_owner_prefix = True

Provided UDA Fields
-------------------

+--------------------+--------------------+--------------------+
| Field Name         | Description        | Type               |
+====================+====================+====================+
| ``bitbucketid``    | Issue ID           | Text (string)      |
+--------------------+--------------------+--------------------+
| ``bitbuckettitle`` | Title              | Text (string)      |
+--------------------+--------------------+--------------------+
| ``bitbucketurl``   | URL                | Text (string)      |
+--------------------+--------------------+--------------------+
