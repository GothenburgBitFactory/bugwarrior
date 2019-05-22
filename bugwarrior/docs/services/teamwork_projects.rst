Teamworks Project
=================

You can import tasks from Teamwork Projects using
the ``teamwork_projects`` service name.

Example Service
---------------

Here's an example of a Teamwork Projects target::

    [my_issue_tracker]
    service = teamwork_projects
    teamwork_projects.token = <token>
    teamwork_projects.host = https://test.teamwork_projects.com

You can also feel free to use any of the configuration options described in :ref:`common_configuration_options`.

Provided UDA Fields
-------------------

+-------------------------------+--------------------------+---------------------------+
| Field Name                    | Description              | Type                      |
+===============================+==========================+===========================+
| ``teamwork_url``              | URL                      | Text (string)             |
+-------------------------------+--------------------------+---------------------------+
| ``teamwork_title``            | Title                    | Text (string)             |
+-------------------------------+--------------------------+---------------------------+
| ``teamwork_description_long`` | Desciption               | Text (string)             |
+-------------------------------+--------------------------+---------------------------+
| ``teamwork_project_id``       | Project ID               | Number (numeric)          |
+-------------------------------+--------------------------+---------------------------+
| ``teamwork_id``               | ID                       | Number (numeric)          |
+-------------------------------+--------------------------+---------------------------+
| ``teamwork_status``           | Open/Closed Status       | Text (string              |
+-------------------------------+--------------------------+---------------------------+
