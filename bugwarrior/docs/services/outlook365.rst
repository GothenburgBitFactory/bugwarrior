Outlook 365
===========

You can create tasks from e-mails in your Gmail account using the
``outlook365`` service name.

Additional Dependencies
-----------------------

Install packages needed for Outlook 365 support with:

.. code:: bash

   pip install bugwarrior[outlook365]

Client Secret
-------------

In order to use this service, you need to create an 'app' and create a client
secret file with the client ID and client secret. The following instructions
are from the `O365 documentation`_ (slightly edited for clarity):

#. Login at `Azure Portal (App Registrations)`_
#. Create an app and give it a name (it doesn't really matter what, but
   perhaps include bugwarrior in the name for your own reference).
#. In Supported account types choose "Accounts in any organizational directory
   and personal Microsoft accounts (e.g. Skype, Xbox, Outlook.com)" - unless
   your organization requires something else.
#. Set the redirect uri (Web) to:
   ``https://login.microsoftonline.com/common/oauth2/nativeclient`` and click
   register. You should use your tenant-specific uri if you deviated in the
   previous step.
#. Write down the Application (client) ID. This is the ``client_id``.
#. Under "Certificates & secrets", generate a new client secret. Set the
   expiration to ``never``.
#. Write down the value of the client secret created now. It will be hidden
   later on. This is the ``client_secret``.
#. Under Api Permissions add the delegated permissions for Microsoft Graph. At
   a minimum, we need the following:
      * Mail.Read
      * User.Read
      * offline_access

You should save the ``client_id`` and ``client_secret`` values to a json file
called ``.o365_client_secrets.json`` in your home directory. The file should
look something like:

```
{"client_id": "SOME_LONG_TEXT", "client_secret": "SOME_OTHER_LONG_TEXT"}
```

You can override the location of the client secrets file by setting the
``client_secret_path`` option.

If you're ovrriding this location in order to support multiple accounts, you
should also override the ``authtoken_path`` setting, which is used to store
the resulting token after authentication.

Note that you do not need to provide the file specified in the
``authtoken_path`` setting. This is generated during the Authentication_
process.


.. _O365 documentation: https://pypi.org/project/O365/#authentication

.. _Azure Portal (App Registrations): https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade


Example Service
---------------

::

    [corp_o365_account]
    service = outlook365
    outlook365.query = isFlagged:true
    outlook365.description_template = {{outlook365subject}}

The specified query can be any outlook search term. By default, it will select
flagged emails. One task is created per email (not per thread).


Authentication
--------------

After you configure the Outlook 365 service in your Bugwarrior configuration
file, ``bugwarrior-pull`` will guide you through the authentication process.

Because Bugwarrior normally runs the services as background processes, and
this authentication flow requires keyboard interaction, it would fail (likely
with a ``EOFError: EOF when reading a line``).

In that case, you should run ``bugwarrior-pull --foreground`` which disables
the use of multiple processes. In this case, it would print out a consent URL
(if authentication is needed).

Then,

#. Copy the URL and open it in a browser.
#. Sign in (if required) and consent/grant permissions.
#. The browser will redirect and *may display an empty page*. Copy the URL
   from the browser's address bar.
#. Paste it in the waiting Bugwarrior terminal.
#. Done.

If you set up everything correctly (including the ``offline_access``
permission for your 'app') and use this service relatively frequently (every
few days), you should only be required to do this authentication flow rarely.


Provided UDA Fields
-------------------

+------------------------------+-----------------------+---------------+
| ``outlook365subject``        | Subject               | Text (string) |
+------------------------------+-----------------------+---------------+
| ``outlook365body``           | Body text             | Text (string) |
+------------------------------+-----------------------+---------------+
| ``outlook365weblink``        | URL                   | Text (string) |
+------------------------------+-----------------------+---------------+
| ``outlook365preview``        | Preview/snippet text  | Text (string) |
+------------------------------+-----------------------+---------------+
| ``outlook365conversationid`` | Conversation-ID       | Text (string) |
+---------------------+--------------------------------+---------------+
