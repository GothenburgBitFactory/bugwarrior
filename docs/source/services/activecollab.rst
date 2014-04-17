.. _activecollab3:

ActiveCollab 3
==============

You can import tasks from your ActiveCollab3 instance using
the ``activecollab`` service name.

Instructions
------------

Obtain your user ID and API url by logging in, clicking on your avatar on
the lower left-hand of the page. When on that page, look at the URL. The
number that appears after "/user/" is your user ID.

On the same page, go to Options and API Subscriptions. Generate a read-only
API key and add that to your bugwarriorrc file.

Bugwarrior will only gather tasks and subtasks for projects in your "Favorites"
list. Note that if you have 10 projects in your favorites list, bugwarrior
will make 21 API calls on each run: 1 call to get a list of favorites, then
2 API calls per projects, one for tasks and one for subtasks.

.. note::

   Use of the ActiveCollab3 service requires that the following additional
   python modules be installed.

   - `pypandoc <https://github.com/bebraw/pypandoc>`_
   - `pyac <https://github.com/kostajh/pyac>`_


Example Service
---------------

Here's an example of an activecollab target.
This is only valid for activeCollab 3.x and greater,
see :ref:`activecollab2` for activeCollab2.x.

::

    [my_bug_tracker]
    service = activecollab
    activecollab.url = https://ac.example.org/api.php
    activecollab.key = your-api-key
    activecollab.user_id = 15

Provided UDA Fields
-------------------

+-------------------+-------------------+-------------------+
| Field Name        | Description       | Type              |
+===================+===================+===================+
| ``acbody``        | Body              | Text (string)     |
+-------------------+-------------------+-------------------+
| ``accreatedbyid`` | Created By        | Text (string)     |
+-------------------+-------------------+-------------------+
| ``accreatedon``   | Created On        | Date & Time       |
+-------------------+-------------------+-------------------+
| ``acid``          | ID                | Text (string)     |
+-------------------+-------------------+-------------------+
| ``acname``        | Name              | Text (string)     |
+-------------------+-------------------+-------------------+
| ``acpermalink``   | Permalink         | Text (string)     |
+-------------------+-------------------+-------------------+
| ``acprojectid``   | Project ID        | Text (string)     |
+-------------------+-------------------+-------------------+
| ``actaskid``      | Task ID           | Text (string)     |
+-------------------+-------------------+-------------------+
| ``actype``        | Task Type         | Text (string)     |
+-------------------+-------------------+-------------------+
