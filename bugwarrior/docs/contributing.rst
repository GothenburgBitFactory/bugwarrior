How to Contribute
=================

.. highlight:: console

Setting up your development environment
---------------------------------------

First, make sure you have the necessary :ref:`requirements`.

You should also install the `virtualenv
<https://pypi.python.org/pypi/virtualenv>`_ tool for python.  (I use a wrapper
for it called `virtualenvwrapper
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

Works in progress
-----------------

The best way to get help and feedback before you pour too much time and effort
into your branch is to open a "work in progress" pull request. We will not leave
it open indefinitely if it doesn't seem to be progressing, but there's nothing to
lose in soliciting some pointers and concerns.

Please begin the title of your work in progress pr with "[WIP]" and explain what
remains to be done or what you're having trouble with.
