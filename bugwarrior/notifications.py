import datetime
from bugwarrior.config import asbool

def _get_metadata(issue):
    due = ''
    tags = ''
    priority = ''
    metadata = ''
    if 'project' in issue:
        project = "Project: " + issue['project']
    if 'due' in issue:
        due = "Due: " + datetime.datetime.fromtimestamp(int(issue['due'])).strftime('%Y-%m-%d')
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
            applicationName = "Bugwarrior",
            notifications = ["New Updates", "New Messages"],
            defaultNotifications = ["New Messages"],
        )
        growl.register()
        if op == 'bw_finished':
            growl.notify(
                noteType = "New Messages",
                title = "Bugwarrior",
                description = "Finished querying for new issues.\n%s" % issue,
                sticky = asbool(conf.get('notifications', 'finished_querying_sticky', 'True')),
                icon = "https://upload.wikimedia.org/wikipedia/en/5/59/Taskwarrior_logo.png",
                priority = 1,
            )
            return
        message = "%s task: %s" % (op, issue['description'].encode("utf-8"))
        metadata = _get_metadata(issue)
        if metadata is not None:
            message += metadata
        growl.notify(
            noteType = "New Messages",
            title = "Bugwarrior",
            description = message,
            sticky = asbool(conf.get('notifications', 'task_crud_sticky', 'True')),
            icon = "https://upload.wikimedia.org/wikipedia/en/5/59/Taskwarrior_logo.png",
            priority = 1,
        )
        return
