Teamwork Projects
=================

You can import tasks from Teamwork Projects using
the ``teamwork_projects`` service name.

Example Service
---------------

Here's an example of a Teamwork Projects target:

.. config::

    [my_issue_tracker]
    service = teamwork_projects
    teamwork_projects.token = <token>
    teamwork_projects.host = https://test.teamwork_projects.com

You can also feel free to use any of the configuration options described in :ref:`common_configuration_options`.

Provided UDA Fields
-------------------

.. udas:: bugwarrior.services.teamwork_projects.TeamworkIssue
