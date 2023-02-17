Git-Bug
=======

You can import tasks from your Git-Bug instance using the ``gitbug`` service name.

This service requires `git-bug <https://github.com/MichaelMure/git-bug#installation>`_ to be installed and available to bugwarrior.

Example Service
---------------

Here's an example of a Git-Bug target::

   [my_issue_tracker]
   service = "gitbug"
   path = "/path/to/gitbug-repo"


The above example is the minimum required to import issues from Git-Bug.  You can also feel free to use any of the configuration options described in :ref:`common_configuration_options` or described in `Service Features`_ below.

The ``path`` should point to the location of your local Git-Bug repo.

Service Features
----------------

Import Labels as Tags
+++++++++++++++++++++

The Git-Bug issue tracker allows you to attach labels to bugs to use those labels as tags, you can use the ``import_labels_as_tags`` option::

    import_labels_as_tags = true

Also, if you would like to control how these labels are created, you can specify a template used for converting the Git-Bug label into a Taskwarrior tag.

For example, to prefix all incoming labels with the string 'gitbug\_' (perhaps to differentiate them from any existing tags you might have), you could add the following configuration option::

    label_template = "gitbug_{{label}}"

In addition to the context variable ``{{label}}``, you also have access
to all fields on the Taskwarrior task if needed.

.. note::

   See :ref:`field_templates` for more details regarding how templates
   are processed.

Port
++++

By default, this service will spin up a git-bug instance served on port 43915. To change the port, assign::

    port = 12345

.. note::

   You'll need to assign ports if you have multiple Git-Bug targets so that bugwarrior can run the Git-Bug server instances concurrently.

Provided UDA Fields
-------------------

.. udas:: bugwarrior.services.gitbug.GitBugIssue
