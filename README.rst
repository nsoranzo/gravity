========================================
 gravity - Galaxy Server Administration
========================================

A process manager (`supervisor`_) and management tools for `Galaxy`_ servers.

Installing this will give you two executables, ``galaxyctl`` which is used to manage the starting, stopping, and logging
of Galaxy's various processes, and ``galaxy``, which can be used to run a Galaxy server in the foreground.

Installation
============

Python 3.7 or later is required. Gravity can be installed independently of Galaxy, but please read the section on Galaxy
Integration below.

To install::

    $ pip install gravity

To make your life easier, you are encourged to install into a `virtualenv`_. The easiest way to do this is with Python's
built-in `venv`_ module::

    $ python3 -m venv ~/gravity
    $ . ~/gravity/bin/activate

By default, Gravity will store its state, configuration, and log files in ``$XDG_CONFIG_HOME/galaxy-gravity``, where
``$XDG_CONFIG_HOME`` typically defaults to ``~/.config``. You can change this with the ``--state-dir`` option to the
Gravity commands, or by setting ``$GRAVITY_STATE_DIR`` in your environment.

Galaxy 22.01 Integration
========================

Gravity was originally designed to support managing multiple Galaxy (as well as Galaxy Reports and Tool Shed) servers on
a single host, but hides some of this complexity from you if you are working with a single Galaxy server. Additionally,
Galaxy 22.01 has added Gravity as a dependency, and changes have been made to Gravity to support this mode of operation.

- Gravity 0.9.0 has dropped support for running Galaxy with uWSGI in favor of `gunicorn`_ and `FastAPI`_.
- Gravity 0.9.0 cannot be used with Galaxy versions older than 22.01.
- As of Galaxy 22.01, Gravity is automatically installed into Galaxy's virtualenv by Galaxy's setup scripts (as called
  by ``run.sh``)
- Galaxy's setup scripts as of 22.01 also set ``$GRAVITY_STATE_DIR`` to ``<galaxy_root>/database/gravity`` when running
  Galaxy from the source directory. This keeps each Galaxy instance's Gravity configuration separate.

Usage
=====

If running from the root of a Galaxy source tree, you can start and run Galaxy in the foreground with::

    $ galaxy
    Registered galaxy config: /home/nate/work/galaxy/config/galaxy.yml
    Creating or updating service gunicorn
    Creating or updating service celery
    Creating or updating service celery-beat
    celery: added process group
    2022-01-20 14:44:24,619 INFO spawned: 'celery' with pid 291651
    celery-beat: added process group
    2022-01-20 14:44:24,620 INFO spawned: 'celery-beat' with pid 291652
    gunicorn: added process group
    2022-01-20 14:44:24,622 INFO spawned: 'gunicorn' with pid 291653
    celery                           STARTING
    celery-beat                      STARTING
    gunicorn                         STARTING
    ==> /home/nate/work/galaxy/database/gravity/log/gunicorn.log <==
    ...log output follows...

Galaxy will continue to run and output logs to stdout until terminate it with ``CTRL+C``.

The ``galaxy`` command is actually a shortcut for three separate steps: 1. Register your Galaxy configuration file
(``galaxy.yml``) with Gravity, 2. write out the process manager configurations, and 3. start and run Galaxy in the
foreground using the process manager (`supervisor`_). You can perform these steps separately (and in this example, start
Galaxy as a backgrounded daemon instead of in the foreground)::

    $ galaxyctl register config/galaxy.yml
    Registered galaxy config: /home/nate/work/galaxy/config/galaxy.yml
    $ galaxyctl update
    Creating or updating service gunicorn
    Creating or updating service celery
    Creating or updating service celery-beat
    $ galaxyctl start
    celery                           STARTING
    celery-beat                      STARTING
    gunicorn                         STARTING
    Log files are in /home/nate/work/galaxy/database/gravity/log

When running as a daemon, the ``stop`` subcommand stops your Galaxy server::

    $ galaxyctl stop
    celery-beat: stopped
    gunicorn: stopped
    celery: stopped
    All processes stopped, supervisord will exit
    Shut down

Once a Galaxy configuration file has been registered with Gravity, it doesn't matter where you call ``galaxy`` or
``galaxyctl`` from.

Configuration
=============

The following options in the ``galaxy`` section of ``galaxy.yml`` can be used to control Gravity::
unset are shown)::

    # Override the default instance name, this is mostly hidden from you when running a single instance # of Galaxy
    instance_name: _default_

    # Application server, either gunicorn (default) or unicornherder
    app_server: gunicorn

    # Application/web server bind address (default: localhost), use 0.0.0.0 for all interfaces on host
    bind_address: localhost

    # Application/web server bind port (default: 8080)
    bind_port: 8080

    # Path to Galaxy source if not running from the source directory
    galaxy_root:

    # Path to directory where log files will be written (default: $GRAVITY_STATE_DIR/log)
    log_dir:

    # Number of dynamic job handler processes to start (default: web server handles jobs)
    job_handler_count:

    # Template for dynamic job handler server naming (default: job-handler-{instance_number})
    job_handler_name_template:

Regarding choices for the ``app_server`` option:

- `gunicorn`_ (default): The Gunicorn Python WSGI server
- `unicornherder`_: Production-oriented manager for (G)unicorn servers that allows for zero-downtime Galaxy server
  restarts, similar to uWSGI Zerg Mode used in the past.

Galaxy Job Handlers
-------------------

Gravity has limited support for reading Galaxy's job configuration: it can read statically configured job handlers in
the ``job_conf.xml`` file, but cannot read the newer YAML-format job configuration, or the job configuration inline from
``galaxy.yml``. Improved support for reading Galaxy's job configuration is planned, but for the time being, Gravity will
run standalone Galaxy job handler processes if you:

1. Set ``job_handler_count`` to a number greater than ``0``. **NOTE:** You must also explicitly set the `job handler
   assignment method`_ to ``db-skip-locked`` or ``db-transaction-isolation`` to prevent the web process from also
   handling jobs. This is the preferred method for specifying job handlers.
2. Define static ``<handler id="..."/>`` handlers in the XML-format job configuration file.

Configuration Precendence
-------------------------

Gravity's configuration is defined in Galaxy's configuration file to be easy and familiar for Galaxy administrators, but
Gravity maintains its own state in ``$GRAVITY_STATE_DIR/configstate.yaml``.  **If set**, the options in ``galaxy.yml``
will override Gravity's saved state whenever ``galaxyctl update`` is run, but if later **unset**, then the persisted
values in Gravity's saved state are used.

The exception is the values of ``app_server`` and ``job_handler_*``, which will revert to default values if unset in
``galaxy.yml``, because Gravity dynamically adds and removes services based on the Galaxy configuration by design.

Subcommands
===========

Use ``galaxyctl --help`` for help. Subcommands also support ``--help``, e.g. ``galaxy register --help``

register
--------

Register a Galaxy server config (``galaxy.yml``) with Gravity. Does not update or start. Run ``galaxyctl update`` after
registering to apply changes.

list
----

List config files registered with the process manager.

deregister
----------

Deregister a Galaxy server config, Gravity will no longer manage this Galaxy instance. Run ``galaxyctl update`` after
deregistering to apply changes.

start
-----

Start and run Galaxy and associated processes in daemonized (background) mode, or ``-f`` to run in the foreground and
follow log files. The ``galaxy`` command is a shortcut for ``galaxyctl start -f``.

If no config files are registered and you run ``galaxyctl start`` from the root of a Galaxy source tree, it
automatically runs the equivalent of::

    $ galaxyctl register config/galaxy.yml  # or galaxy.yml.sample if galaxy.yml does not exist
    $ galaxyctl update
    $ galaxyctl start

stop
----

Stop daemonized Galaxy server processes. If no processes remain running after this step (which should be the case when
working with a single Galaxy instance), ``supervisord`` will terminate.

restart
-------

Restart Galaxy server processes. This is done in a relatively "brutal" fashion: processes are signaled (by supervisor)
to exit, and then are restarted. See the ``graceful`` subcommand to restart gracefully.

graceful
--------

Restart Galaxy with minimal interruption. If running with `gunicorn`_ this means holding the web socket open while
restarting (connections to Galaxy will block). If running with `unicornherder`_, a new Galaxy application will be
started and the old one shut down only once the new one is accepting connections. A graceful restart with unicornherder
should be transparent to clients.

update
------

Figure out what has changed in configs, which could be:

-  changes to the Gravity configuration options in ``galaxy.yml``
-  adding or removing handlers in ``job_conf.xml``

This may cause service restarts if there are any changes.

Any needed changes to supervisor configs will be performed and then ``supervisorctl update`` will be called.

``update`` is called automatically for the ``start``, ``stop``, ``restart``, and ``graceful`` subcommands.

shutdown
--------

Stop all processes and cause ``supervisord`` to terminate. Similar to ``stop`` but there is no ambiguity as to whether
``supervisord`` remains running.

supervisorctl
-------------

Pass through directly to supervisor. Run ``galaxyctl supervisorctl`` to invoke the supervisorctl shell, or ``galaxyctl
supervisorctl [command]`` to call a supervisorctl command directly. See the `supervisor`_ documentation or ``galaxyctl
supervisorctl help`` for help.

instances
---------

List known (configured) Galaxy instances and services.

show
----

Show stored configuration details for the named config file.

rename
------

If your ``galaxy.yml`` has moved, you can update its path in Gravity's saved state with this command.

configstate.yaml
================

As discussed in the Configuration section, Gravity maintains a state file that also acts as a configuration of sorts.
Administrators deploying Galaxy with a deployment tool (e.g. `Ansible`_) can take advantage of this to deploy a Gravity
state file as part of their Galaxy deployment. See the ``$GRAVITY_STATE_DIR/configstate.yaml`` file after performing a
``register`` and ``update`` command to see what this file looks like, or below for an example. Keep in mind that running
``galaxyctl`` commands after changing the Galaxy configuration can cause changes to the state file because it was not
originally intended to be user-maintainable. See `Issue #6`_ for discussion and development related to this, as we seek
to provide a more consistent experience in working with Gravity's configuration.

Example
-------

A ``configstate.yaml`` file for a Galaxy service might look like::

    config_files:
      /home/nate/work/galaxy/config/galaxy.yml:
        config_type: galaxy
        instance_name: _default_
        attribs:
          app_server: gunicorn
          log_dir: /home/nate/work/galaxy/database/gravity/log
          bind_address: localhost
          bind_port: 8080
          galaxy_root: /home/nate/work/galaxy
        services:
        - config_type: galaxy
          service_type: gunicorn
          service_name: gunicorn
        - config_type: galaxy
          service_type: celery
          service_name: celery
        - config_type: galaxy
          service_type: celery-beat
          service_name: celery-beat

.. _supervisor: http://supervisord.org/
.. _Galaxy: http://galaxyproject.org/
.. _virtualenv: https://virtualenv.pypa.io/
.. _venv: https://docs.python.org/3/library/venv.html
.. _gunicorn: https://gunicorn.org/
.. _FastAPI: https://fastapi.tiangolo.com/
.. _unicornherder: https://github.com/alphagov/unicornherder
.. _job handler assignment method: https://docs.galaxyproject.org/en/master/admin/scaling.html#job-handler-assignment-methods
.. _Ansible: http://www.ansible.com/
.. _Issue #6: https://github.com/galaxyproject/gravity/issues/6
