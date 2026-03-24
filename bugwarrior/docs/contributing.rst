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

   Requires pip >= 25.1 for `dependency group <https://peps.python.org/pep-0735/>`_ support.

   .. code-block:: bash

    $ mkdir .venv
    $ python -m venv .venv
    $ source .venv/bin/activate
    $ pip install --upgrade "pip>=25.1"
    $ pip install -e .[all]
    $ pip install --group test

.. tab:: uv

   .. code-block:: bash

    $ uv sync --all-extras --group test

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

We use ruff for linting and formatting and ty for type checking. These are
checked in the test suite, so you don't necessarily need to worry about them
separately, but you may find it convenient to run ``ruff check``, ``ruff
format``, and ``ty check``, or `integrate ruff with your editor
<https://docs.astral.sh/ruff/editors/setup/>`_.

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
