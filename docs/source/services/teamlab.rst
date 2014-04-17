Teamlab
=======

You can import tasks from your Teamlab instance using
the ``teamlab`` service name.

Example Service
---------------

Here's an example of an Teamlab target::

    [my_issue_tracker]
    service = teamlab
    teamlab.hostname = teamlab.example.com
    teamlab.login = alice
    teamlab.password = secret
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
