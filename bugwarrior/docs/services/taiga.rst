Taiga
=====

You can import tasks from a Taiga instance using the ``taiga`` service name.

Example Service
---------------

Here's an example of a taiga project::

    [my_issue_tracker]
    service = taiga
    taiga.base_uri = http://taiga.fedorainfracloud.org
    taiga.auth_token = ayJ1c4VyX2F1dGhlbnQpY2F0aW9uX2lmIjo1fQ:2a2LPT:qscLbfQC_jyejQsICET5KgYNPLM

The above example is the minimum required to import issues from Taiga.  You can
also feel free to use any of the configuration options described in
:ref:`common_configuration_options`.

Service Features
----------------
By default, userstories from taiga are added in taskwarrior. If you like to include taiga tasks as well, set the config option::

    taiga.include_tasks = True

Provided UDA Fields
-------------------

+---------------------+---------------------+---------------------+
| Field Name          | Description         | Type                |
+=====================+=====================+=====================+
| ``taigaid``         | Issue ID            | Text (string)       |
+---------------------+---------------------+---------------------+
| ``taigasummary``    | Summary             | Text (string)       |
+---------------------+---------------------+---------------------+
| ``taigaurl``        | URL                 | Text (string)       |
+---------------------+---------------------+---------------------+

The Taiga service provides a limited set of UDAs.  If you have need for some
other values not present here, please file a request (there's lots of metadata
in there that we could expose).
