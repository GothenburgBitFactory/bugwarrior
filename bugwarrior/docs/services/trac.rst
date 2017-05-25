Trac
====

You can import tasks from your Trac instance using
the ``trac`` service name.

Additional Dependencies
-----------------------

Install packages needed for Trac support with::

    pip install bugwarrior[trac]

Example Service
---------------

Here's an example of a Trac target::

    [my_issue_tracker]
    service = trac
    trac.base_uri = fedorahosted.org/moksha
    trac.scheme = https
    trac.project_template = moksha.{{traccomponent|lower}}

By default, this service uses the XML-RPC Trac plugin, which must be installed
on the Trac instance.  If this is not available, the service can use Trac's
built-in CSV support, but in this mode it cannot add annotations based on
ticket comments.  To enable this mode, add ``trac.no_xmlrpc = true``.

If your trac instance requires authentication to perform the query, add::

    trac.username = ralph
    trac.password = OMG_LULZ

The above example is the minimum required to import issues from
Trac.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`.

Service Features
----------------

Provided UDA Fields
-------------------

+-------------------+-----------------+-----------------+
| Field Name        | Description     | Type            |
+===================+=================+=================+
| ``tracnumber``    | Number          | Text (string)   |
+-------------------+-----------------+-----------------+
| ``tracsummary``   | Summary         | Text (string)   |
+-------------------+-----------------+-----------------+
| ``tracurl``       | URL             | Text (string)   |
+-------------------+-----------------+-----------------+
| ``traccomponent`` | Component       | Text (string)   |
+-------------------+-----------------+-----------------+
