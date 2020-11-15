HTTP
=====

Receive tasks from HTTP services such as APIs.

Additional Dependencies
-----------------------

Install packages needed for HTTP support with:

.. code:: bash

   pip install bugwarrior[http]

Example Service
---------------

Here's an example of a HTTP target:

::

    [my_api]
    service = http
    http.url = "https://example.com/tasks"

Example response from APIs
--------------------------

In order to create a task  correctly, the HTTP endpoint needs to return data in the following format:

::

    [
        {
            "tags": ["home", "garden"],
            "entry": "20200709T141933Z",
            "description": "Attempting to scare those annoying cats away",
            "uuid": "8ce52fe2-ec48-489d-ba00-c30f463fc422",
            "modified": "20200709T141933Z",
            "project": "AnnoyingCats"
        }
    ]

Possibly other attributes such as annotations or priority will be implemented later on.

Other settings
++++++++++++++

+--------------------------------+---------------------------------------------------------------------------------+
| ``http.method``                | HTTP method to use, such as GET or POST.                                        |
+--------------------------------+---------------------------------------------------------------------------------+
| ``http.authorization_header``  | Header for authorization, useable for Bearer-tokens, Basic-Authentication, etc. |
+--------------------------------+---------------------------------------------------------------------------------+

Provided UDA Fields
-------------------

+---------------------+-----------------------------------+---------------+
| ``http_uuid``       | UUID for task in service          | Text (string) |
+---------------------+-----------------------------------+---------------+
| ``http_url``        | URL used to retrieve task         | Text (string) |
+---------------------+-----------------------------------+---------------+
