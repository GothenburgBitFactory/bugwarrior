from twiggy import log
import subprocess
import datetime

def send_notification(issue, op, conf):
    notify_binary = conf.get('general', 'notifications')
    if notify_binary == 'pync':
        from pync import Notifier
        if op == 'bw_finished':
            Notifier.notify('Bugwarrior finished querying for new issues.', title="Bugwarrior", subtitle=issue)
            return
        command = []
        message = issue['description'].encode("utf-8")
        title_text = "%s task: %s" % (op, issue['description'].encode("utf-8")[:20])
        subtitle_text = ''
        due = ''
        tags = ''
        priority = ''
        if 'project' in issue:
            project = "Proj: " + issue['project']
        if 'due' in issue:
            due = "Due: " + str(issue['due'])
        if 'tags' in issue:
            tags = "Tags: " + ', '.join(issue['tags'])
        if 'priority' in issue:
            priority = "Pri: " + issue['priority']
        if project != '':
            subtitle_text += project + " "
        if priority != '':
            subtitle_text += priority + " "
        if due != '':
            subtitle_text += due + " "
        if tags != '':
            subtitle_text += tags + " "
        if 'uuid' in issue:
            execute_cmd = 'task %s' % issue['uuid']
        else:
            execute_cmd = 'task list'
        Notifier.notify(message.translate(None, '(bw)#'), title=title_text, subtitle=subtitle_text, execute=execute_cmd)
