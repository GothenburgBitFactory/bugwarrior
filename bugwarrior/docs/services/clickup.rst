ClickUp
=======

You can import tasks from a Clickup space using
the ``clickup`` service name.

Example Service
---------------

Here's an example of a Clickup target:

.. config::

    [my_issue_tracker]
    service = clickup 
    clickup.token = pk_mytoken
    clickup.team_id = 123456

The above example is the minimum required to import tasks from
Clickup. 

The ``token`` is your private API token. Check 
https://developer.clickup.com/docs/authentication.
The ``team_id`` is the numeric identification of the team.

Provided UDA Fields
-------------------

.. udas:: bugwarrior.services.clickup.ClickupIssue
