import datetime
import os
import urllib

from bugwarrior.config import asbool


cache_dir = os.path.expanduser("~/.cache/bugwarrior")
logo_path = cache_dir + "/logo.png"
logo_url = "https://upload.wikimedia.org/wikipedia/" + \
    "en/5/59/Taskwarrior_logo.png"


def _cache_logo():
    if os.path.exists(logo_path):
        return

    if not os.path.isdir(cache_dir):
        os.makedirs(cache_dir)

    urllib.urlretrieve(logo_url, logo_path)


def _get_metadata(issue):
    due = ''
    tags = ''
    priority = ''
    metadata = ''
    project = ''
    if 'project' in issue:
        project = "Project: " + issue['project']
    # if 'due' in issue:
    #     due = "Due: " + datetime.datetime.fromtimestamp(
    #         int(issue['due'])).strftime('%Y-%m-%d')
    if 'tags' in issue:
        tags = "Tags: " + ', '.join(issue['tags'])
    if 'priority' in issue:
        priority = "Priority: " + issue['priority']
    if project != '':
        metadata += "\n" + project
    if priority != '':
        metadata += "\n" + priority
    if due != '':
        metadata += "\n" + due
    if tags != '':
        metadata += "\n" + tags
    return metadata


def send_notification(issue, op, conf):
    notify_backend = conf.get('notifications', 'backend')

    # Notifications for growlnotify on Mac OS X
    if notify_backend == 'growlnotify':
        import gntp.notifier
        growl = gntp.notifier.GrowlNotifier(
            applicationName="Bugwarrior",
            notifications=["New Updates", "New Messages"],
            defaultNotifications=["New Messages"],
        )
        growl.register()
        if op == 'bw_finished':
            growl.notify(
                noteType="New Messages",
                title="Bugwarrior",
                description="Finished querying for new issues.\n%s" %
                issue['description'],
                sticky=asbool(conf.get(
                    'notifications', 'finished_querying_sticky', 'True')),
                icon="https://upload.wikimedia.org/wikipedia/"
                "en/5/59/Taskwarrior_logo.png",
                priority=1,
            )
            return
        message = "%s task: %s" % (op, issue['description'].encode("utf-8"))
        metadata = _get_metadata(issue)
        if metadata is not None:
            message += metadata
        growl.notify(
            noteType="New Messages",
            title="Bugwarrior",
            description=message,
            sticky=asbool(conf.get(
                'notifications', 'task_crud_sticky', 'True')),
            icon="https://upload.wikimedia.org/wikipedia/"
            "en/5/59/Taskwarrior_logo.png",
            priority=1,
        )
        return
    elif notify_backend == 'pynotify':
        _cache_logo()

        import pynotify
        pynotify.init("bugwarrior")

        if op == 'bw finished':
            message = "Finished querying for new issues.\n%s" %\
                issue['description']
        else:
            message = "%s task: %s" % (
                op, issue['description'].encode("utf-8"))
            metadata = _get_metadata(issue)
            if metadata is not None:
                message += metadata

        pynotify.Notification("Bugwarrior", message, logo_path).show()
    elif notify_backend == 'gobject':
        _cache_logo()

        from gi.repository import Notify
        Notify.init("bugwarrior")

        if op == 'bw finished':
            message = "Finished querying for new issues.\n%s" %\
                issue['description']
        else:
            message = "%s task: %s" % (
                op, issue['description'].encode("utf-8"))
            metadata = _get_metadata(issue)
            if metadata is not None:
                message += metadata

        Notify.Notification.new("Bugwarrior", message, logo_path).show()
