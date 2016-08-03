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
    bitbucket.login = ralphbean
    bitbucket.password = mypassword

The above example is the minimum required to import issues from
Bitbucket.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`.

Note that both ``bitbucket.username`` and ``bitbucket.login`` are required and can be
set to different values.  ``bitbucket.login`` is used to specify what account
bugwarrior should use to login to bitbucket.  ``bitbucket.username`` indicates which
repositories should be scraped.  For instance, I always have ``bitbucket.login``
set to ralphbean (my account).  But I have some targets with
``bitbucket.username`` pointed at organizations or other users to watch issues
there.

As an alternative to password authentication, there is OAuth. To get a key and secret,
go to the "OAuth" section of your profile settings and click "Add consumer". Set the
"Callback URL" to ``https://localhost/`` and set the appropriate permissions. Then
assign your consumer's credentials to ``bitbucket.key`` and ``bitbucket.secret``. Note
that you will have to provide a password (only) the first time you pull, so you may
want to set ``bitbucket.password = @oracle:ask_password`` and run
``bugwarrior-pull --interactive`` on your next pull.

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

Filter Merge Requests
+++++++++++++++++++++

Although you can filter issues using :ref:`common_configuration_options`,
pull requests are not filtered by default.  You can filter pull requests
by adding the following configuration option::

    bitbucket.filter_merge_requests = True

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
