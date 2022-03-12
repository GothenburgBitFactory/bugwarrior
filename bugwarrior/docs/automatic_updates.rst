Automatic Updates
=================

Cron
----

It's ideal to create a cron task like::

    */15 * * * *  /usr/bin/bugwarrior pull

Bugwarrior can emit desktop notifications when it adds or completes issues
to and from your local ``~/.task/`` db.  If your ``bugwarriorrc`` file has
notifications turned on, you'll also need to tell cron which display to use by
adding the following to your crontab::

    DISPLAY=:0
    */15 * * * *  /usr/bin/bugwarrior pull


systemd timer
-------------

If you would prefer to use a systemd timer to run ``bugwarrior pull`` on a
schedule, you can create the following two files::

    $ cat ~/.config/systemd/user/bugwarrior-pull.service
    [Unit]
    Description=bugwarrior pull

    [Service]
    Environment="DISPLAY=:0"
    ExecStart=/usr/bin/bugwarrior pull
    Type=oneshot

    [Install]
    WantedBy=default.target
    $ cat ~/.config/systemd/user/bugwarrior-pull.timer
    [Unit]
    Description=Run bugwarrior pull hourly and on boot

    [Timer]
    OnBootSec=15min
    OnUnitActiveSec=1h

    [Install]
    WantedBy=timers.target

Once those files are in place, you can start and enable the timer::

    $ systemctl --user enable bugwarrior-pull.timer
    $ systemctl --user start bugwarrior-pull.timer
