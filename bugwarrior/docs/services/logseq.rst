Logseq
======

You can import `tasks <https://docs.logseq.com/#/page/tasks>`_ from `Logseq <https://logseq.com/>`_ using the ``logseq`` service name.


Additional Requirements
-----------------------

Logseq application must active with the HTTP API server running for bugwarrior to connect.

To use bugwarrior to pull tickets from Logseq you need to enable the Logseq HTTP APIs server.
In Logseq go to **Settings** > **Features** and toggle the **HTTP APIs server** option.

Next select the **API** option in the top menu to configure authorization token, e.g

.. image:: pictures/logseq_token.png


Example Service
---------------

Here's an example of a Logseq target:

.. config::

    [my_logseq_graph]
    service = logseq
    logseq.host = localhost
    logseq.port = 12315
    logseq.token = mybugwarrioraccesstoken

The above example is the minimum required to import issues from Logseq.
You can also feel free to use any of the configuration options described in
:ref:`common_configuration_options` or described in `Service Features`_ below.

Service Features
----------------

Task filters
++++++++++++

You can configure the service to import tasks in different states.
By default the service will import all tasks in an active tasks states

    DOING, TODO, NOW, LATER, IN-PROGRESS, WAIT, WAITING

You can override this filter by setting the ``logseq.task_state`` option to a 
comma separated list of required task states.

.. config::
    :fragment: logseq

    logseq.task_state = DOING, NOW, IN-PROGRESS

Priority mapping
++++++++++++++++

Logseq task priorities ``A``, ``B``, and ``C`` mapped to the taskwarroior priorities
``H``, ``M``, and ``L`` respectively.

Date and time mapping
+++++++++++++++++++++

The Logseq task SCHEDULED: and DEADLINE: fields are mapped to the ``scheduled`` and ``due`` date fields.

Task state mapping
++++++++++++++++++

``DOING``,``TODO``, ``NOW``, ``IN-PROGRESS`` are mapped to the default ``pending`` state.

``DONE`` is mapped to the ``completed`` state.

``CANCELED`` and ``CANCELLED`` are mapped to the ``deleted`` state.

Character replacement
+++++++++++++++++++++

taskwarrior encodes the `[` and `]` characters commonly used in Logseq as ``&open;`` and ``&close;``. To
avoid display issues ``[[`` and ``]]`` are replaced by ``【`` and ``】`` for page links, and single
``[`` and ``]`` are replaced by ``〈`` and ``〉``. 

You can override behaviour and use customer characters by setting the ``logseq.char_*`` options in your
``bugwarriorrc`` config.

.. config::
    :fragment: logseq

    logseq.char_open_link = 〖
    logseq.char_close_link = 〗
    logseq.char_open_bracket = (
    logseq.char_close_bracket = )

Troubleshooting
---------------

Logseq graph re-index
+++++++++++++++++++++

If you re-index your Logseq graph all task ids and uuids are changed. The next time
you run bugwarrior all existing taskwarrior tasks will be closed and new ones will 
be created.

Logseq API connection issues
++++++++++++++++++++++++++++

If you get the following error when running bugwarrior:

    CRITICAL:bugwarrior.services.logseq:Unable to connect to Logseq HTTP APIs server. HTTPConnectionPool(host='localhost', port=12315): Max retries exceeded with url: /api (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x105764f20>: Failed to establish a new connection: [Errno 61] Connection refused'))

- Check that the LogSeq application is running
- Check that the HTTP APIs server is started
- Check that authorization token is set the APIs server settings and matches the 
  ``logseq.token`` in your ``bugwarriorrc`` 

Provided UDA Fields
-------------------

.. udas:: bugwarrior.services.logseq.LogseqIssue
