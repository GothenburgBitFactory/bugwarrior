Megaplan
========

You can import tasks from your Megaplan instance using
the ``megaplan`` service name.

Additional Requirements
-----------------------

Install the following package using ``pip``:

* ``megaplan``

Example Service
---------------

Here's an example of a Megaplan target::

    [my_issue_tracker]
    service = megaplan
    megaplan.hostname = example.megaplan.ru
    megaplan.login = alice
    megaplan.password = secret
    megaplan.project_name = example

The above example is the minimum required to import issues from
Megaplab.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`.

Provided UDA Fields
-------------------

+-------------------+-------------------+-------------------+
| Field Name        | Description       | Type              |
+===================+===================+===================+
| ``megaplanid``    | Issue ID          | Text (string)     |
+-------------------+-------------------+-------------------+
| ``megaplantitle`` | Title             | Text (string)     |
+-------------------+-------------------+-------------------+
| ``megaplanurl``   | URL               | Text (string)     |
+-------------------+-------------------+-------------------+
