from twiggy import log
import subprocess
import datetime

def _get_metadata(issue):
    due = ''
    tags = ''
    priority = ''
    metadata = ''
    if 'project' in issue:
        project = "Project: " + issue['project']
    if 'due' in issue:
        due = "Due: " + str(datetime.datetime.strptime(issue['due'], "%Y%m%dT%H%M%SZ"))
    if 'tags' in issue:
        tags = "Tags: " + ', '.join(issue['tags'])
    if 'priority' in issue:
        priority = "Priority: " + issue['priority']
    if project != '':
        metadata += project + "\n"
    if priority != '':
        metadata += priority + "\n"
    if due != '':
        metadata += due + "\n"
    if tags != '':
        metadata += tags + " "
    return metadata

def send_notification(issue, op, conf):
    notify_binary = conf.get('general', 'notifications')

    # Notifications for growlnotify on Mac OS X
    if notify_binary == 'growlnotify':
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
                sticky = True,
                icon = "https://upload.wikimedia.org/wikipedia/en/5/59/Taskwarrior_logo.png",
                priority = 1,
            )
            return
        message = "%s task: %s" % (op, issue['description'].encode("utf-8"))
        metadata = _get_metadata(issue)
        if metadata is not None:
            message += "\n%s" % metadata
        growl.notify(
            noteType = "New Messages",
            title = "Bugwarrior",
            description = message,
            sticky = True,
            icon = "https://upload.wikimedia.org/wikipedia/en/5/59/Taskwarrior_logo.png",
            priority = 1,
        )
        return
