.. _activecollab4:

ActiveCollab 4
==============

You can import tasks from your activeCollab 4.x instance using
the ``activecollab`` service name.

Additional Requirements
-----------------------

Install the following packages using ``pip``:

* ``pypandoc``
* ``pyac``

Instructions
------------

Obtain your user ID and API url by logging in, clicking on your avatar on
the lower left-hand of the page. When on that page, look at the URL. The
number that appears after "/user/" is your user ID.

On the same page, go to Options and API Subscriptions. Generate a read-only
API key and add that to your bugwarriorrc file.

Bugwarrior will gather tasks and subtasks returned from the `my-tasks` API call.
Additional API calls will be made to gather comments associated with each task.

.. note::

   Use of the ActiveCollab service requires that the following additional
   python modules be installed.

   - `pypandoc <https://github.com/bebraw/pypandoc>`_
   - `pyac <https://github.com/kostajh/pyac>`_


Example Service
---------------

Here's an example of an activecollab target.
This is only valid for activeCollab 4.x and greater,
see :ref:`activecollab2` for activeCollab2.x.

::

    [my_bug_tracker]
    service = activecollab
    activecollab.url = https://ac.example.org/api.php
    activecollab.key = your-api-key
    activecollab.user_id = 15

The above example is the minimum required to import issues from
ActiveCollab 4.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`.

Provided UDA Fields
-------------------

+---------------------+-----------------+----------------+
| Field Name          | Description     | Type           |
+=====================+=================+================+
| ``acbody``          | Body            | Text (string)  |
+---------------------+-----------------+----------------+
| ``accreatedbyname`` | Created By Name | Text (string)  |
+---------------------+-----------------+----------------+
| ``accreatedon``     | Created On      | Date & Time    |
+---------------------+-----------------+----------------+
| ``acid``            | ID              | Text (string)  |
+---------------------+-----------------+----------------+
| ``acname``          | Name            | Text (string)  |
+---------------------+-----------------+----------------+
| ``acpermalink``     | Permalink       | Text (string)  |
+---------------------+-----------------+----------------+
| ``acprojectid``     | Project ID      | Text (string)  |
+---------------------+-----------------+----------------+
| ``actaskid``        | Task ID         | Text (string)  |
+---------------------+-----------------+----------------+
| ``actype``          | Task Type       | Text (string)  |
+---------------------+-----------------+----------------+
| ``acestimatedtime`` | Estimated Time  | Text (numeric) |
+---------------------+-----------------+----------------+
| ``actrackedtime``   | Tracked Time    | Text (numeric) |
+---------------------+-----------------+----------------+
| ``acmilestone``     | Milestone       | Text (string)  |
+---------------------+-----------------+----------------+
