Contributing
============

.. highlight:: console

Setting up your development environment
---------------------------------------

First, make sure you have the necessary :ref:`requirements`.

Next step -- get the code!

::

    $ git clone git@github.com:GothenburgBitFactory/bugwarrior.git
    $ cd bugwarrior

Now use your favorite tool to attain an editable installation.

.. tab:: pip

   .. code-block:: bash

    $ mkdir .venv
    $ python -m venv .venv
    $ source .venv/bin/activate
    $ pip install -e .[all]

.. tab:: uv

   .. code-block:: bash

    $ uv sync --all-extras

The following will actually run it...be careful and back up your task directory!

.. tab:: pip

   .. code-block:: bash

    $ bugwarrior pull

.. tab:: uv

   .. code-block:: bash

    $ uv run bugwarrior pull


To run the tests, use ``pytest``:

.. tab:: pip

   .. code-block:: bash

    $ pytest

.. tab:: uv

   .. code-block:: bash

    $ uv run pytest

We use ruff for linting and formatting. This is checked in the test suite, so
you don't necessarily need to worry about it separately, but you may find it
convenient to run ``ruff check`` and ``ruff format`` or `integrate ruff with
your editor <https://docs.astral.sh/ruff/editors/setup/>`_.

Making a pull request
---------------------

Create a new branch for each pull request based off the ``develop`` branch::

    $ git checkout -b my-shiny-new-feature develop

Make your changes, push your branch to your fork of the repository, and create
a new PR using the normal GitHub flow.

We look forward to your contribution!

Works in progress
-----------------

The best way to get help and feedback before you pour too much time and effort
into your branch is to open a "work in progress" pull request. We will not leave
it open indefinitely if it doesn't seem to be progressing, but there's nothing to
lose in soliciting some pointers and concerns.

Please begin the title of your work in progress pr with "[WIP]" and explain what
remains to be done or what you're having trouble with.
