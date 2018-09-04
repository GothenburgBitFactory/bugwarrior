Gmail
=====

You can create tasks from e-mails in your Gmail account using the ``gmail``
service name.

Additional Dependencies
-----------------------

Install packages needed for Gmail support with:

.. code:: bash

   pip install bugwarrior[gmail]

Client Secret
-------------

In order to use this service, you need to create a product and download a
client secret file. Do this by following the instructions on:
``https://developers.google.com/gmail/api/quickstart/python``. You should save
the resulting secret in your home directory as ``.gmail_client_secret.json``.
You can override this location by setting the ``client_secret_path`` option.

Example Service
---------------

Here's an example of a gmail target:

::

    [my_gmail]
    service = gmail
    gmail.query = label:action OR label:readme
    gmail.login_name = you@example.com

The specified query can be any gmail search term. By default it will select
starred threads. One task is created per selected thread, not per e-mail.

You do not need to specify the ``login_name``, but it can be useful to avoid
accidentally fetching data from the wrong account. (This also allows multiple
targets with the same login to share the same authentication token.)

Authentication
--------------

When you first run ``bugwarrior-pull``, a browser will be opened and you'll be
asked to authorise the application to access your e-mail. Once authorised a
token will be stored in your bugwarrior data directory.

Provided UDA Fields
-------------------

+---------------------+-----------------------------------+---------------+
| ``gmailthreadid``   | Thread Id                         | Text (string) |
+---------------------+-----------------------------------+---------------+
| ``gmailsubject``    | Subject                           | Text (string) |
+---------------------+-----------------------------------+---------------+
| ``gmailurl``        | URL                               | Text (string) |
+---------------------+-----------------------------------+---------------+
| ``gmaillastsender`` | Last Sender's Name                | Text (string) |
+---------------------+-----------------------------------+---------------+
| ``gmaillastsender`` | Last Sender's E-mail Address      | Text (string) |
+---------------------+-----------------------------------+---------------+
| ``gmailsnippet``    | Snippet of text from conversation | Text (string) |
+---------------------+-----------------------------------+---------------+
