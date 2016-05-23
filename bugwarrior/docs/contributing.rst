How to Contribute
=================

.. highlight:: console

Setting up your development environment
---------------------------------------

You should install the `virtualenv <https://pypi.python.org/pypi/virtualenv>`_
tool for python.  (I use a wrapper for it called `virtualenvwrapper
<https://pypi.python.org/pypi/virtualenvwrapper>`_ which is awesome but not
required.)  Virtualenv will help isolate your dependencies from the rest of
your system.

::

    $ sudo yum install python-virtualenv git
    $ mkdir -p ~/virtualenvs/
    $ virtualenv ~/virtualenvs/bugwarrior

You should now have a virtualenv in a ``~/virtualenvs/`` directory.
To use it, you need to "activate" it like this::

    $ source ~/virtualenv/bugwarrior/bin/activate
    (bugwarrior)$ which python

At any time, you can deactivate it by typing ``deactivate`` at the command
prompt.

Next step -- get the code!

::

    (bugwarrior)$ git clone git@github.com:ralphbean/bugwarrior.git
    (bugwarrior)$ cd bugwarrior
    (bugwarrior)$ python setup.py develop
    (bugwarrior)$ which bugwarrior-pull

This will actually run it.. be careful and back up your task directory!

::

    (bugwarrior)$ bugwarrior-pull

Making a pull request
---------------------

Create a new branch for each pull request based off the ``develop`` branch::

    (bugwarrior)$ git checkout -b my-shiny-new-feature develop

Please add tests when appropriate and run the test suite before opening a PR::

    (bugwarrior)$ python setup.py nosetests

We look forward to your contribution!
