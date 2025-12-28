Creating a New Service
======================

In this tutorial we will walk through the process of writing a new service from scratch with examples from `git-bug <https://github.com/MichaelMure/git-bug>`_. In the process we will get a high level overview of each component of a service. Let's get started!

1. API Access
-------------

The first step is figuring out how you're going to establish a connection to your service's API.

You may choose to use an existing python client for accessing the API if an existing library already exists. If you're going this route, be sure to add an entry to the ``[project.optional-dependencies]`` table in ``pyproject.toml``. You should also go ahead and test this library out in a python interpreter and make sure you can authenticate with an external server if necessary.

More likely you'll be writing your own client using an http API, so start off by making sure you can access it on the command line with, for example, curl.

.. code:: bash

  curl 'http://127.0.0.1:12345/graphql' \
    -H 'Content-Type: application/json' \
    --data-binary '{"query":"{ repository { allBugs { nodes { title } } } }"}'

This example of accessing a local service is quite simple, but you'll likely need to pass additional arguments and perhaps go through a handshake process to authenticate to a remote server.

2. Initialize Service
---------------------

There are two approaches here, depending on whether your service will be maintained in bugwarrior or will be maintained separately as a :doc:`third party service <third_party>`. We don't have a strict criteria, but the best candidates for services maintained within bugwarrior tend to satisfy most of the following considerations:

- open source (or useful free tier)
- popularity
- maturity (not a new startup)
- public API documentation

If you're sure you're going to be upstreaming your service, clone the bugwarrior repo and create a python file with the name of your service in ``bugwarrior/services``.

.. code:: bash

   touch bugwarrior/services/gitbug.py

If you're going to maintain your service in it's own repository or if you're uncertain if it will be accepted upstream, create a new package for it.

.. code:: bash

   cd $MY_PROJECTS
   mkdir bugwarrior-gitbug
   cd bugwarrior-gitbug
   touch bugwarrior_gitbug.py

3. Imports
----------

Fire up your favorite editor and import the base classes and whatever library you're using to access your service.

.. code:: python

  import logging
  import pathlib
  import typing

  import requests

  from bugwarrior import config
  from bugwarrior.services import Service, Issue, Client

  log = logging.getLogger(__name__)

We're going to step through the use of these bugwarrior classes in subsequent sections, but for reference you may find the :doc:`API docs <api>` helpful.


4. Configuration Schema
-----------------------

Now define an initial configuration schema as follows. Don't worry, we're about to break this down!

.. code:: python

  class GitbugConfig(config.ServiceConfig):
      service: typing.Literal['gitbug']

      path: pathlib.Path

      import_labels_as_tags: bool = False
      label_template: str = '{{label}}'
      port: int = 43915

This class is a `pydantic <https://pydantic-docs.helpmanual.io/>`_ model which we use to define which configuration options are available for the service, validate user configurations, and pass these values on to the service.

The ``service`` attribute is how bugwarrior will know to assign a given section of the configuration file to your service, for example:

.. config::

  [my_gitbug]
  service = gitbug

The ``path`` is the only particular detail required to access our local git-bug instance. You'll likely need additional details such as a username and token to authenticate to the service. Look at how you accessed the API in step 1 and ask yourself which components need to be configurable.

The ``import_labels_as_tags`` and ``port`` attributes create optional configuration fields to allow customization of bugwarrior behavior.

.. note::
   A common pitfall when writing a new service is to add configuration options for functionality that is already provided by :ref:`field_templates`. This is a powerful feature which makes many configurable features unnecessary.

4. Client
---------

Unless you're using a library that closely aligns with the needs of your service class, you'll probably want a client class. The purpose of this class is to abstract away the details of getting the data we need from the API -- authenticating, querying, paging, de-serializing, etc. -- so your service can focus on the business of translating service data into taskwarrior tasks.

.. code:: python

  class GitBugClient(Client):
      def __init__(self, path, port):
          self.path = path
          self.port = port

      def _query_graphql(self, query):
          response = requests.post(
              f'http://127.0.0.1:{self.port}/graphql',
              json={'query': query})
          return self.json_response(response)['data']

      def get_issues(self):
          return self._query_graphql('{ repository { allBugs { nodes { title } } } }')

As you see, our client provides a simple API to execute the same API query we did in step 1. We can come back and add the additional fields bugwarrior will need to fetch later.

5. Issue
--------

We will now implement an ``Issue`` class, which is essentially a wrapper for each task you're pulling in. This provides a consistent API across services, which enables bugwarrior to synchronize arbitrary tasks without knowing anything about the service they come from.

.. code:: python

  class GitbugIssue(Issue):
      AUTHOR = 'gitbugauthor'
      ID = 'gitbugid'
      STATE = 'gitbugstate'
      TITLE = 'gitbugtitle'

      UDAS = {
          AUTHOR: {'type': 'string', 'label': 'Gitbug Issue Author'},
          ID: {'type': 'string', 'label': 'Gitbug UUID'},
          STATE: {'type': 'string', 'label': 'Gitbug state'},
          TITLE: {'type': 'string', 'label': 'Gitbug Title'},
      }

      UNIQUE_KEY = (ID,)

      def to_taskwarrior(self):
          return {
              'project': self.extra['project'],
              'priority': self.config.default_priority,
              'annotations': self.record.get('annotations', []),
              'tags': self.get_tags(),
              'entry': self.parse_date(self.record.get('createdAt')),

              self.AUTHOR: self.record['author']['name'],
              self.ID: self.record['id'],
              self.STATE: self.record['state'],
              self.TITLE: self.record['title'],
          }

      def get_tags(self):
          return self.get_tags_from_labels(
              [label['name'] for label in self.record['labels']])

      def get_default_description(self):
          return self.build_default_description(title=self.record['title'], cls='bug')

The first thing you see here is the declaration of which UDAs this service will assign to each task. The first set of class attributes define the UDA names -- e.g. the author will be assigned to ``gitbugauthor`` -- and the ``UDAS`` dictionary provides additional metadata about them.

The ``UNIQUE_KEY`` attribute must be assigned a tuple of UDAs which are sufficient to identify a task. Keep in mind that these will be used to update tasks when their remote content changes, so the selected UDAs must be immutable.

There are two abstract methods which now must be implemented: ``to_taskwarrior`` and ``get_default_description``.

The first must return a dictionary of attributes -- both the standard attributes and UDAs -- pointing to their content in a given issue. This content will largely be found in the ``record`` and ``extra`` attributes, which we will get to later.

The ``get_default_description`` method must return a string representation of the task using the ``build_default_description`` method, which takes the following keyword arguments, all optional:

- title
- url
- number
- cls (a categorization of the type of task, defaulting to "issue")

6. Service
----------

Now for the main service class which bugwarrior will invoke to fetch issues.

.. code:: python

  class GitBugService(Service):
      API_VERSION = 1.0
      ISSUE_CLASS = GitBugIssue
      CONFIG_SCHEMA = GitBugConfig

      def __init__(self, *args, **kwargs):
          super().__init__(*args, **kwargs)

          self.client = GitBugClient(
              path=self.config.path,
              port=self.config.port,
              annotation_comments=self.main_config.annotation_comments)

      @staticmethod
      def get_keyring_service(config):
          return f'gitbug://{config.path}'

      def issues(self):
          for issue in self.client.get_issues():
              comments = issue.pop('comments')
              issue['description'] = comments['nodes'].pop(0)['message']

              if self.main_config.annotation_comments:
                  annotations = ((
                      comment['author']['name'],
                      comment['message']
                  ) for comment in comments['nodes'])
                  issue['annotations'] = self.build_annotations(annotations)

              yield self.get_issue_for_record(issue)

Here we see three required class attributes and two required methods.

The ``API_VERSION`` is set to the latest, while the other two attributes point to our previously defined classes.

The ``get_keyring_service`` method returns a string identifier for secrets in the keyring. Ideally, this string uniquely identifies a given instance of the service when it is possible to have multiple instances of the service configured.

The ``issues`` method is a generator which yields individual issue dictionaries.

.. note::

  Sensitive configuration values should be fetched with ``self.get_secret()`` so that they can be optionally retrieved with :ref:`oracles <Secret Management>`.

.. note::

   When relevant and reasonably feasible, all services should implement the :ref:`common_configuration_options`:

   - ``only_if_assigned`` and ``also_unassigned``: These options are usually implemented either in the service by filtering retrieved tasks or (ideally) in the client by increasing the specificity of the api query.
   - ``default_priority``: This is generally implemented by adding an ``ISSUE_MAP`` class attribute to the ``Issue`` class and using the ``get_priority`` method in ``to_taskwarrior``. When the service does not provide a relevant "priority" value, this configuration value can be assigned directly.
   - ``add_tags``: You need not worry about this one, it is implemented automatically.

7. Service Registration
-----------------------

If you're developing your service in a separate package, it's time to create a ``pyproject.toml`` if you have not done so already, and register the name of your service with the path to your ``Service`` class.

.. code:: toml

  [project.entry-points."bugwarrior.service"]
  gitbug = "bugwarrior.services.gitbug:GitBugService"

If you're developing in the bugwarrior repo, you can simply add your entry to the existing ``[project.entry-points."bugwarrior.service"]`` table.

8. Tests
----------

.. note::

   The remainder of this tutorial is not geared towards third-party services. While you are free to use bugwarrior's testing infrastructure, no attempt is being made to maintain the stability of these interfaces at this time.



Create a test file and implement at least the minimal service tests by inheriting from ``AbstractServiceTest``.

.. code:: bash

   touch tests/test_gitbug.py

.. code:: python

  class TestGitBugIssue(AbstractServiceTest, ServiceTest):
      SERVICE_CONFIG = {
          'service': 'gitbug',
          'path': '/dev/null',
      }

      def setUp(self):
          super().setUp()

          self.data = TestData()

          self.service = self.get_mock_service(GitBugService)
          self.service.client = mock.MagicMock(spec=GitBugClient)
          self.service.client.get_issues = mock.MagicMock(
              return_value=[self.data.arbitrary_bug])

      def test_to_taskwarrior(self):
          issue = self.service.get_issue_for_record(
              self.data.arbitrary_bug, {})

          expected = { ... }

          actual = issue.to_taskwarrior()

          self.assertEqual(actual, expected)

      def test_issues(self):
          issue = next(self.service.issues())

          expected = { ... }

          self.assertEqual(TaskConstructor(issue).get_taskwarrior_record(), expected)

9. Documentation
------------------

Create a documentation file and include the relevant sections.

.. code:: bash

   touch bugwarrior/docs/services/gitbug.rst

Copy and complete the following template:

.. code::

   SERVICE_NAME
   ============

   You can import tasks from your SERVICE_NAME instance using the ``SERVICE`` service name.

   EXTRA DEPENDENCY INSTALLATION INSTRUCTIONS, IF NEEDED

   Example Service
   ---------------

   Here's an example of a SERVICE_NAME target:

   .. config::

       [my_issue_tracker]
       service = SERVICE
       ADDITIONAL REQUIRED CONFIGURATION OPTIONS, IN INI FORMAT


   The above example is the minimum required to import issues from SERVICE_NAME.
   You can also feel free to use any of the configuration options described in :ref:`common_configuration_options` or described in `Service Features`_ below.

   EXPLAIN THE ADDITIONAL REQUIRED CONFIGURATION OPTIONS

   Service Features
   ----------------

   ADD SECTIONS HERE TO COVER EACH OPTIONAL CONFIGURATION OPTION.
   SOME OPTIONS WILL NEED THEIR OWN SECTION WHILE OTHERS MAKE SENSE TO GROUP TOGETHER.

   Provided UDA Fields
   -------------------

   .. udas:: bugwarrior.services.SERVICE_MODULE.ISSUE_CLASS

10. README
----------

Update the list of services in ``README.rst`` with a link to the homepage of your service.
