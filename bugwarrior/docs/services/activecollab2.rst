.. _activecollab2:

ActiveCollab 2
==============

You can import tasks from your ActiveCollab2 instance using
the ``activecollab2`` service name.

Instructions
------------

You can obtain your user ID and API url by logging into ActiveCollab and
clicking on "Profile" and then "API Settings". When on that page, look
at the URL. The integer that appears after "/user/" is your user ID.

Projects should be entered in a comma-separated list, with the project
id as the key and the name you'd like to use for the project in Taskwarrior
entered as the value. For example, if the project ID is 8 and the project's
name in ActiveCollab is "Amazing Website" then you might enter 8:amazing_website

Note that due to limitations in the ActiveCollab API, there is no simple way
to get a list of all tasks you are responsible for in AC. Instead you need to
look at each ticket that you are subscribed to and check to see if your
user ID is responsible for the ticket/task. What this means is that if you
have 5 projects you want to query and each project has 20 tickets, you'll
make 100 API requests each time you run ``bugwarrior-pull``.

Example Service
---------------

Here's an example of an activecollab2 target. Note that this will only work
with ActiveCollab 2.x - see above for 3.x and greater.

::

    [my_bug_tracker]
    services = activecollab2
    activecollab2.url = http://ac.example.org/api.php
    activecollab2.key = your-api-key
    activecollab2.user_id = 15
    activecollab2.projects = 1:first_project, 5:another_project

The above example is the minimum required to import issues from
ActiveCollab 2.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`.

Provided UDA Fields
-------------------

+--------------------+--------------------+--------------------+
| Field Name         | Description        | Type               |
+====================+====================+====================+
| ``ac2body``        | Body               | Text (string)      |
+--------------------+--------------------+--------------------+
| ``ac2createdbyid`` | Created By         | Text (string)      |
+--------------------+--------------------+--------------------+
| ``ac2createdon``   | Created On         | Date & Time        |
+--------------------+--------------------+--------------------+
| ``ac2name``        | Name               | Text (string)      |
+--------------------+--------------------+--------------------+
| ``ac2permalink``   | Permalink          | Text (string)      |
+--------------------+--------------------+--------------------+
| ``ac2projectid``   | Project ID         | Text (string)      |
+--------------------+--------------------+--------------------+
| ``ac2ticketid``    | Ticket ID          | Text (string)      |
+--------------------+--------------------+--------------------+
| ``ac2type``        | Task Type          | Text (string)      |
+--------------------+--------------------+--------------------+
