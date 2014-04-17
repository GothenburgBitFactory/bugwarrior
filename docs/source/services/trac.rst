Trac
====

You can import tasks from your Trac instance using
the ``trac`` service name.

Example Service
---------------

Here's an example of an Trac target::

    [my_issue_tracker]
    service = trac
    trac.base_uri = fedorahosted.org/moksha
    trac.username = ralph
    trac.password = OMG_LULZ

.. note::

   Your Trac installation must have the XML-RPC plugin enabled
   for Bugwarrior to work.

The above example is the minimum required to import issues from
Trac.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`.

Service Features
----------------

Provided UDA Fields
-------------------

+-----------------+-----------------+-----------------+
| Field Name      | Description     | Type            |
+=================+=================+=================+
| ``tracnumber``  | Number          | Text (string)   |
+-----------------+-----------------+-----------------+
| ``tracsummary`` | Summary         | Text (string)   |
+-----------------+-----------------+-----------------+
| ``tracurl``     | URL             | Text (string)   |
+-----------------+-----------------+-----------------+
