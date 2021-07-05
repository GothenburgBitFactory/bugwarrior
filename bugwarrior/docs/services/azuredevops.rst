Azure DevOps
============

You can import tasks from Azure DevOps instance using
the ``azuredevops`` service name.


Example Service
---------------

Here's an example of a jira project::

    [my_issue_tracker]
    service = azuredevops
    ado.PAT = 1234abcd5678efgh
    ado.project = testproject
    ado.organization = testorganization

.. note::

   If you look at a work item in the browser, the url should be something like https://dev.azure.com/testorganziation/testproject/_workitems/edit/12345/


The above example is the minimum required to import issues from
Azure DevOps.  You can also feel free to use any of the
configuration options described in :ref:`common_configuration_options`
or described in `Service Features`_ below.

Service Features
----------------

The following default configuration is used::

    ado.host = dev.azure.com
    ado.wiql_filter = SELECT [System.Id] FROM workitems WHERE [System.AssignedTo] = @me


Specify the Query to Use for Gathering Issues
+++++++++++++++++++++++++++++++++++++++++++++

By default, the Azure DevOps plugin will include any issues that are assigned to you, but you can fine-tune the query used
for gathering issues by setting the ``ado.wiql_filter`` parameter. This parameter will not replace the default filter, but will append
your query to the end of the filter with an ``AND`` keyword. 

For example, to select issues only in an active state 
configuration option::

    ado.wiql_filter = [System.State] = 'Active'

Provided UDA Fields
-------------------

+---------------------+--------------------------------+---------------------+
| Field Name          | Description                    | Type                |
+=====================+================================+=====================+
| ``adodescription``  | Description                    | Text (string)       |
+---------------------+--------------------------------+---------------------+
| ``adoid``           | Issue ID                       | Decimal (numeric)   |
+---------------------+--------------------------------+---------------------+
| ``adotitle``        | Title                          | Text (string)       |
+---------------------+--------------------------------+---------------------+
| ``adourl``          | URL                            | Text (string)       |
+---------------------+--------------------------------+---------------------+
| ``adoremainingwork``| Remaining Work                 | Decimal (numeric)   |
+---------------------+--------------------------------+---------------------+
| ``adostate``        | State                          | Text (string)       |
+---------------------+--------------------------------+---------------------+
| ``adotype``         | Issue Type                     | Text (string)       |
+---------------------+--------------------------------+---------------------+
| ``adoactivity``     | Fix Version                    | Text (String)       |
+---------------------+--------------------------------+---------------------+
| ``adopriority``     | Priority                       | Decimal (numeric)   |
+---------------------+--------------------------------+---------------------+
| ``adoparent``       | Parent Task                    | Text (string)       |
+---------------------+--------------------------------+---------------------+
| ``adonamespace``    | Namespace                      | Text (string)       |
+---------------------+--------------------------------+---------------------+
