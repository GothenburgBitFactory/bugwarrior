How to use
==========

Just run ``bugwarrior-pull``.

Cron
----

It's ideal to create a cron task like::

    */15 * * * *  /usr/bin/bugwarrior-pull

Bugwarrior can emit desktop notifications when it adds or completes issues
to and from your local ``~/.task/`` db.  If your ``bugwarriorrc`` file has
notifications turned on, you'll also need to tell cron which display to use by
adding the following to your crontab::

    DISPLAY=:0
    */15 * * * *  /usr/bin/bugwarrior-pull


systemd timer
-------------

If you would prefer to use a systemd timer to run ``bugwarrior-pull`` on a
schedule, you can create the following two files::

    $ cat ~/.config/systemd/user/bugwarrior-pull.service 
    [Unit]
    Description=bugwarrior-pull

    [Service]
    Environment="DISPLAY=:0"
    ExecStart=/usr/bin/bugwarrior-pull
    Type=oneshot

    [Install]
    WantedBy=default.target
    $ cat ~/.config/systemd/user/bugwarrior-pull.timer 
    [Unit]
    Description=Run bugwarrior-pull hourly and on boot

    [Timer]
    OnBootSec=15min
    OnUnitActiveSec=1h

    [Install]
    WantedBy=timers.target

Once those files are in place, you can start and enable the timer::

    $ systemctl --user enable bugwarrior-pull.timer 
    $ systemctl --user start bugwarrior-pull.timer


Exporting a list of UDAs
------------------------

Most services define a set of UDAs in which bugwarrior store extra information
about the incoming ticket.  Usually, this includes things like the title
of the ticket and its URL, but some services provide an extensive amount of
metadata.  See each service's documentation for more information.

For using this data in reports, it is recommended that you add these UDA
definitions to your ``taskrc`` file.  You can generate your list of
UDA definitions by running the following command::

    bugwarrior-uda

You can add those lines verbatim to your ``taskrc`` file if you would like
Taskwarrior to know the human-readable name and data type for the defined
UDAs.

.. note::

   Not adding those lines to your ``taskrc`` file will have no negative
   effects aside from Taskwarrior not knowing the human-readable name for the
   field, but depending on what version of Taskwarrior you are using, it
   may prevent you from changing the values of those fields or using them
   in filter expressions.

