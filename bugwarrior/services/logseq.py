import logging

import requests
import typing_extensions

import re
from datetime import datetime

from bugwarrior import config
from bugwarrior.services import IssueService, Issue, ServiceClient

log = logging.getLogger(__name__)


class LogseqConfig(config.ServiceConfig):
    service: typing_extensions.Literal["logseq"]
    host: str = "localhost"
    port: int = 12315
    token: str
    task_state: config.ConfigList = [
        "DOING", "TODO", "NOW", "LATER", "IN-PROGRESS", "WAIT", "WAITING"
        # states DONE and CANCELED/CANCELLED are skipped by default
    ]
    char_open_link: str = "【"
    char_close_link: str = "】"
    char_open_bracket: str = "〈"
    char_close_bracket: str = "〉"
    inline_links: bool = True


class LogseqClient(ServiceClient):
    def __init__(self, host, port, token, filter):
        self.host = host
        self.port = port
        self.token = token
        self.filter = filter

        self.headers = {
            "Authorization": "Bearer " + self.token,
            "content-type": "application/json; charset=utf-8",
        }

    def _datascript_query(self, query):
        try:
            response = requests.post(
                f"http://{self.host}:{self.port}/api",
                headers=self.headers,
                json={"method": "logseq.DB.datascriptQuery", "args": [query]},
            )
            return self.json_response(response)
        except requests.exceptions.ConnectionError as ce:
            log.fatal("Unable to connect to Logseq HTTP APIs server. %s", ce)
            exit(1)

    def _get_current_graph(self):
        try:
            response = requests.post(
                f"http://{self.host}:{self.port}/api",
                headers=self.headers,
                json={"method": "logseq.getCurrentGraph", "args": []},
            )
            return self.json_response(response)
        except requests.exceptions.ConnectionError as ce:
            log.fatal("Unable to connect to Logseq HTTP APIs server. %s", ce)
            exit(1)

    def get_graph_name(self):
        graph = self._get_current_graph()
        return graph["name"] if graph else None

    def get_issues(self):
        query = f"""
            [:find (pull ?b [*])
                :where [?b :block/marker ?marker]
                [(contains? #{{{self.filter}}} ?marker)]
            ]
        """
        result = self._datascript_query(query)
        if "error" in result:
            log.fatal("Error querying Logseq: %s using query %s", result["error"], query)
            exit(1)
        return result


class LogseqIssue(Issue):
    ID = "logseqid"
    UUID = "logsequuid"
    STATE = "logseqstate"
    TITLE = "logseqtitle"
    DONE = "logseqdone"
    URI = "logsequri"

    # Local 2038-01-18, with time 00:00:00.
    # A date far away, with semantically meaningful to GTD users.
    # see https://taskwarrior.org/docs/dates/
    SOMEDAY = datetime(2038, 1, 18)

    UDAS = {
        ID: {
            "type": "string",
            "label": "Logseq ID",
        },
        UUID: {
            "type": "string",
            "label": "Logseq UUID",
        },
        STATE: {
            "type": "string",
            "label": "Logseq State",
        },
        TITLE: {
            "type": "string",
            "label": "Logseq Title",
        },
        DONE: {
            "type": "date",
            "label": "Logseq Done",
        },
        URI: {
            "type": "string",
            "label": "Logseq URI",
        },
    }

    UNIQUE_KEY = (ID, UUID)

    # map A B C priority to H M L
    PRIORITY_MAP = {
        "A": "H",
        "B": "M",
        "C": "L",
    }

    # `pending` is the defuault state. Taskwarrior will dynamcily change task to `waiting`
    # state if wait date is set to a future date.
    STATE_MAP = {
        "IN-PROGRESS": "pending",
        "DOING": "pending",
        "TODO": "pending",
        "NOW": "pending",
        "LATER": "pending",
        "WAIT": "pending",
        "WAITING": "pending",
        "DONE": "completed",
        "CANCELED": "deleted",
        "CANCELLED": "deleted",
    }

    # replace characters that cause escaping issues like [] and "
    # this is a workaround for https://github.com/ralphbean/taskw/issues/172
    def _unescape_content(self, content):
        return (
            content.replace('"', "'")  # prevent &dquote; in task details
            .replace("[[", self.config.char_open_link)  # alternate brackets for linked items
            .replace("]]", self.config.char_close_link)
            .replace("[", self.config.char_open_bracket)  # prevent &open; and &close;
            .replace("]", self.config.char_close_bracket)
        )

    # remove brackets and spaces to compress display format of mutli work tags
    # e.g from #[[Multi Word]] to #MultiWord
    def _compress_tag_format(self, tag):
        return (
            tag.replace(self.config.char_open_link, "")
            .replace(" ", "")
            .replace(self.config.char_close_link, "")
        )

    # get an optimized and formatted title
    def get_formated_title(self):
        # use first line only and remove priority
        first_line = (
            self.record["content"]
            .split("\n")[0]  # only use first line
            .replace("[#A] ", "")  # remove priority markers
            .replace("[#B] ", "")
            .replace("[#C] ", "")
        )
        return self._unescape_content(first_line)

    # get a list of tags from the task content
    def get_tags_from_content(self):
        # this includes #tagname, but ignores tags that are in the #[[tag name]] format
        tags = re.findall(
            r"(#[^" + self.config.char_open_link + r"^\s]+)",
            self.get_formated_title()
        )
        # and this add teh #[[multi word]] formated tags
        tags.extend(re.findall(
            r"(#[" + self.config.char_open_link + r"].*[" + self.config.char_close_link + r"])",
            self.get_formated_title()
        ))
        # compress format to single words
        tags = [self._compress_tag_format(t) for t in tags]
        return tags

    # get a list of annotations from the content
    def get_annotations_from_content(self):
        annotations = []
        scheduled_date = None
        deadline_date = None
        for line in self.record["content"].split("\n"):
            # handle special annotations
            if line.startswith("SCHEDULED: "):
                scheduled_date = self.get_scheduled_date(line)
            elif line.startswith("DEADLINE: "):
                deadline_date = self.get_scheduled_date(line)
            else:
                annotations.append(self._unescape_content(line))
        annotations.pop(0)  # remove first line
        return annotations, scheduled_date, deadline_date

    def get_url(self):
        return f'logseq://graph/{self.extra["graph"]}?block-id={self.record["uuid"]}'

    def get_logseq_state(self):
        return self.record["marker"]

    def get_scheduled_date(self, scheduled):
        # format is <YYYY-MO-DD DAY HH:MM .+1d>
        # e.g. <2024-06-20 Thu 10:55 .+1d>
        date_split = (
            scheduled.replace("DEADLINE: <", "")
            .replace("SCHEDULED: <", "")
            .replace(">", "")
            .split(" ")
        )
        if len(date_split) == 2:  # <date day>
            date = date_split[0]
            date_format = "%Y-%m-%d"
        elif len(date_split) == 3 and (date_split[2][0] in ("+", ".")):  # <date day repeat>
            date = date_split[0]
            date_format = "%Y-%m-%d"
        elif len(date_split) == 3:  # <date day time>
            date = date_split[0] + " " + date_split[2]
            date_format = "%Y-%m-%d %H:%M"
        elif len(date_split) == 4:  # <date date time repeat>
            date = date_split[0] + " " + date_split[2]
            date_format = "%Y-%m-%d %H:%M"
        else:
            log.warning(f"Could not determine date format from {scheduled}")
            return None

        try:
            return datetime.strptime(date, date_format)
        except ValueError:
            log.warning(f"Could not parse date {date} from {scheduled}")
        return None

    def _is_waiting(self):
        return self.get_logseq_state() in ["WAIT", "WAITING"]

    def to_taskwarrior(self):
        annotations, scheduled_date, deadline_date = self.get_annotations_from_content()
        wait_date = min([d for d in [scheduled_date, deadline_date, self.SOMEDAY] if d is not None])
        return {
            "project": self.extra["graph"],
            "priority": (
                self.PRIORITY_MAP[self.record["priority"]]
                if "priority" in self.record
                else None
            ),
            "annotations": annotations,
            "tags": self.get_tags_from_content(),
            "due": deadline_date,
            "scheduled": scheduled_date,
            "wait": wait_date if self._is_waiting() else None,
            "status": self.STATE_MAP[self.get_logseq_state()],
            self.ID: self.record["id"],
            self.UUID: self.record["uuid"],
            self.STATE: self.record["marker"],
            self.TITLE: self.get_formated_title(),
            self.URI: self.get_url(),
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.get_formated_title(),
            url=self.get_url() if self.config.inline_links else '',
            number=self.record["id"],
            cls="issue",
        )


class LogseqService(IssueService):
    ISSUE_CLASS = LogseqIssue
    CONFIG_SCHEMA = LogseqConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        filter = '"' + '" "'.join(self.config.task_state) + '"'
        self.client = LogseqClient(
            host=self.config.host,
            port=self.config.port,
            token=self.config.token,
            filter=filter,
        )

    def get_owner(self, issue):
        # Issue assignment hasn't been implemented yet.
        raise NotImplementedError(
            "This service has not implemented support for 'only_if_assigned'."
        )

    def issues(self):
        graph_name = self.client.get_graph_name()
        for issue in self.client.get_issues():
            extra = {"graph": graph_name}
            yield self.get_issue_for_record(issue[0], extra)
