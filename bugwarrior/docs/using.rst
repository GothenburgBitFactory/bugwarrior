How to use
==========

Just run ``bugwarrior-pull``.

It's ideal to create a cron task like::

    */15 * * * *  /usr/bin/bugwarrior-pull

Bugwarrior can emit desktop notifications when it adds or completes issues
to and from your local ``~/.task/`` db.  If your ``~/.bugwarriorrc`` file has
notifications turned on, you'll also need to tell cron which display to use by
adding the following to your crontab::

    DISPLAY=:0
    */15 * * * *  /usr/bin/bugwarrior-pull
