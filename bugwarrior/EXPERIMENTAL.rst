bugwarrior experimental
=======================

Bugwarrior has an experimental mode that utilizes the TaskWarriorExperimental
class from `taskw <https://github.com/ralphbean/taskw>`_.

Usage
-----


1. Update to TaskWarrior 2.2.0 stable.

2. Backup your task completed, pending, and undo files! 

3. In the ``[general]`` section of your ``.bugwarriorrc``, add ``experimental = True``

4. Now create a bugwarrior taskrc file at ``~/.bugwarrior_taskrc``. Create a ``.bugwarrior-tasks`` directory (probably next to your existing ``.tasks`` directory). The contents of the ``~/.bugwarrior_taskrc`` file should be:

.. example

::

  data.location=/path/to/.bugwarrior-tasks
  json.array=true
  color=off
  verbose=nothing
  taskw.experimental=true

.. example

5. Run ``bugwarrior-pull``. Here's a run through of what happens:

- Bugwarrior will load the ``~/.bugwarrior_taskrc`` that you created.
- All tasks will be synced to the ``data.location`` defined in Bugwarriors taskrc. 
- ``task merge`` is called, which will update or create tasks in the primary TaskWarrior database.
- ``task done`` is called to complete any tasks in the primary TaskWarrior database, since task merge won't complete tasks, just update/create.
- ``task delete`` is called on all tasks in Bugwarrior's task database. (They are not permanently removed from ``completed.data``, just marked as deleted.)

It's worth noting that annotation updates won't be handled due to limitations in TaskWarrior but this will hopefully be fixed in TW 2.3.0.
