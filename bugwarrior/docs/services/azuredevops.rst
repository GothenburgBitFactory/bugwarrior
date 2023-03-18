Azure DevOps
============

You can import tasks from Azure DevOps instance using
the ``azuredevops`` service name.


Example Service
---------------

Here's an example of a azure devops project:

.. config::

    [my_issue_tracker]
    service = azuredevops
    ado.PAT = 1234abcd5678efgh
    ado.project = testproject1
    ado.organization = testorganization

.. note::

   If you look at a work item in the browser, the url should be something like https://dev.azure.com/testorganziation/testproject/_workitems/edit/12345/



The above example is the minimum required to import issues from
Azure DevOps.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`
or described in `Service Features`_ below.

The PAT (Personal Access Token) can be generated for your project by following https://docs.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate

Service Features
----------------

The following default configuration is used:

.. config::
    :fragment: azuredevops

    ado.host = dev.azure.com
    ado.wiql_filter = SELECT [System.Id] FROM workitems


Specify the Query to Use for Gathering Issues
+++++++++++++++++++++++++++++++++++++++++++++

By default, the Azure DevOps plugin will include all issues in the project, but you can fine-tune the query used
for gathering issues by setting the ``wiql_filter`` parameter.
Please note there is a limit imposed by the Azure DevOps API on the number of workitems you can pull at the same time (20000). If your query exceeds this limitation, the application will produce an error.
A good default would be to only pull ado workitem assigned to yourself. Do that with this query:
configuration option:

.. config::
    :fragment: azuredevops

    ado.wiql_filter = [System.AssignedTo] = @me


To select issues only in an active state
configuration option:

.. config::
    :fragment: azuredevops

    ado.wiql_filter = [System.AssignedTo] = @me AND [System.State] = 'Active'

Provided UDA Fields
-------------------

.. udas:: bugwarrior.services.azuredevops.AzureDevopsIssue
