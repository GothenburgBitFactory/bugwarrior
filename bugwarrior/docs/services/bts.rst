Debian Bug Tracking System (BTS)
================================

You can import tasks from the Debian Bug Tracking System (BTS) using
the ``bts`` service name. Debian's bugs are public and no authentication
information is required by bugwarrior for this service.

Additional Requirements
-----------------------

You will need to install the following additional packages via ``pip``:

 * ``PySimpleSOAP``
 * ``python-debianbts``

.. note:: If you have installed the Debian package for bugwarrior, this
          dependency will already be satisfied.

Example Service
---------------

Here's an example of a Debian BTS target::

    [debian_bts]
    service = bts
    bts.email = username@debian.org

The above example is the minimum required to import issues from
the Debian BTS.  You can also feel free to use any of the configuration options
described in :ref:`common_configuration_options` or described in `Service
Features`_ below.

Service Features
----------------

Include all bugs for packages
+++++++++++++++++++++++++++++

If you would like more bugs than just those you are the owner of, you can specify
the ``bts.packages`` option.

For example if you wanted to include bugs on the ``hello`` package, you can add
this line to your service configuration::

    bts.packages = hello

More packages can be specified seperated by commas.

Ultimate Debian Database (UDD) Bugs Search
++++++++++++++++++++++++++++++++++++++++++

If you maintain a large number of packages and you wish to include bugs from all
packages where you are listed as a Maintainer or an Uploader in the Debian archive,
you can enable the use of the `UDD Bugs Search <https://udd.debian.org/bugs/>`_.

This will peform a search and include the bugs from the result. To enable this
feature, you can add this line to your service configuration::

    bts.udd = True

Excluding bugs marked pending
+++++++++++++++++++++++++++++

Debian bugs are not considered closed until the fixed package is present in the
Debian archive. Bugs do cease to be outstanding tasks however as soon as you have
completed the work, and so it can be useful to exclude bugs that you have marked
with the pending tag in the BTS.

This is the default behaviour, but if you feel you would like to include bugs that
are marked as pending in the BTS, you can disable this by adding this line to your
service configuration::

    bts.ignore_pending = False

Excluding sponsored and NMU'd packages
++++++++++++++++++++++++++++++++++++++

If you maintain an even larger number of packages, you may wish to exclude some
packages.

You can exclude packages that you have sponsored or have uploaded as a
non-maintainer upload or team upload by adding the following line to your
service configuration::

    bts.udd_ignore_sponsor = True

.. note:: This will only affect the bugs returned by the UDD bugs search service
          and will not exclude bugs that are discovered due to ownership or due
          to packages explicitly specified in the service configuration.

Excluding packages explicitly
+++++++++++++++++++++++++++++

If you would like to exclude a particularly noisy package, that is perhaps team
maintained, or a package that you have orphaned and no longer have interest in but
are still listed as Maintainer or Uploader in stable suites, you can explicitly
ignore bugs based on their binary or source package names. To do this add one
of the following lines to your service configuration::

    bts.ignore_pkg = hello,anarchism
    bts.ignore_src = linux

.. note:: The ``src:`` prefix that is commonly seen in the Debian BTS interface
          is not required when specifying source packages to exclude.

Provided UDA Fields
-------------------

+---------------------+---------------------+---------------------+
| Field Name          | Description         | Type                |
+=====================+=====================+=====================+
| ``btsnumber``       | Bug Number          | Text (string)       |
+---------------------+---------------------+---------------------+
| ``btsurl``          | bugs.d.o URL        | Text (string)       |
+---------------------+---------------------+---------------------+
| ``btssubject``      | Subject             | Text (string)       |
+---------------------+---------------------+---------------------+
| ``btssource``       | Source Package      | Text (string)       |
+---------------------+---------------------+---------------------+
| ``btspackage``      | Binary Package      | Text (string)       |
+---------------------+---------------------+---------------------+
| ``btsforwarded``    | Forwarded URL       | Text (string)       |
+---------------------+---------------------+---------------------+
| ``btsstatus``       | Status              | Text (string)       |
+---------------------+---------------------+---------------------+

