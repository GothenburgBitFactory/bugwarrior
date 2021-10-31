Teamlab
=======

You can import tasks from your Teamlab instance using
the ``teamlab`` service name.

Example Service
---------------

Here's an example of a Teamlab target::

    [my_issue_tracker]
    service = teamlab
    teamlab.hostname = teamlab.example.com
    teamlab.login = alice
    teamlab.password = secret

The above example is the minimum required to import issues from
Teamlab. You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`.

Service Features
----------------

Project Name
++++++++++++

By default the project name is set to the hostname. To set a different name::

    teamlab.project_name = example_teamlab


Provided UDA Fields
-------------------

+---------------------------+---------------------------+---------------------------+
| Field Name                | Description               | Type                      |
+===========================+===========================+===========================+
| ``teamlabid``             | ID                        | Text (string)             |
+---------------------------+---------------------------+---------------------------+
| ``teamlabprojectownerid`` | ProjectOwner ID           | Text (string)             |
+---------------------------+---------------------------+---------------------------+
| ``teamlabtitle``          | Title                     | Text (string)             |
+---------------------------+---------------------------+---------------------------+
| ``teamlaburl``            | URL                       | Text (string)             |
+---------------------------+---------------------------+---------------------------+
