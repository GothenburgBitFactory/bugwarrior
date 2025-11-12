import logging
import typing

import requests

import re
from datetime import datetime

from bugwarrior import config
from bugwarrior.services import Service, Issue, Client

log = logging.getLogger(__name__)


class LogseqConfig(config.ServiceConfig):
    service: typing.Literal["logseq"]
    host: str = "localhost"
    port: int = 12315
    token: str
    task_state: config.ConfigList = ["Doing", "Todo", "In Review", "Backlog"]
    char_open_link: str = "【"
    char_close_link: str = "】"
    char_open_bracket: str = "〈"
    char_close_bracket: str = "〉"
    inline_links: bool = True
    import_labels_as_tags: bool = False
    label_template: str = "{{label}}"

    only_if_assigned: config.UnsupportedOption[str] = ""
    also_unassigned: config.UnsupportedOption[bool] = False


class LogseqClient(Client):
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
                json={"method": "logseq.App.getCurrentGraph", "args": []},
            )
            return self.json_response(response)
        except requests.exceptions.ConnectionError as ce:
            log.fatal("Unable to connect to Logseq HTTP APIs server. %s", ce)
            exit(1)

    def get_graph_name(self):
        graph = self._get_current_graph()
        return graph["name"] if graph else None

    def get_page(self, page_id):
        try:
            response = requests.post(
                f"http://{self.host}:{self.port}/api",
                headers=self.headers,
                json={"method": "logseq.Editor.getPage", "args": [page_id]},
            )
            return self.json_response(response)
        except requests.exceptions.ConnectionError as ce:
            log.fatal("Unable to connect to Logseq HTTP APIs server. %s", ce)
            exit(1)

    def get_issues(self):
        # In DB mode, blocks have :db/id, status is at :logseq.property/status with {:db/id N}
        # We need to query for blocks and join with status entities
        query = f"""
            [:find (pull ?b [* {{:logseq.property/status [:block/title]}}])
             :where
               [?b :block/uuid _]
               (or-join [?b]
                 ;; Classic mode: marker as direct attribute
                 (and
                   [?b :block/marker ?marker]
                   [(contains? #{{{self.filter}}} ?marker)]
                 )
                 ;; DB mode: status reference with :db/id
                 (and
                   [?b :logseq.property/status ?status-ref]
                   [?status-ref :block/title ?status-name]
                   [(contains? #{{{self.filter}}} ?status-name)]
                 )
               )
            ]
        """

        result = self._datascript_query(query)
        if "error" in result:
            log.fatal(
                "Error querying Logseq: %s using query %s", result["error"], query
            )
            exit(1)

        log.info(f"Found {len(result)} tasks matching filter: {self.filter}")
        return result


class LogseqIssue(Issue):
    ID = "logseqid"
    UUID = "logsequuid"
    STATE = "logseqstate"
    TITLE = "logseqtitle"
    DONE = "logseqdone"
    URI = "logsequri"
    SCHEDULED = "logseqscheduled"
    DEADLINE = "logseqdeadline"
    PAGE = "logseqpage"

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
        SCHEDULED: {"type": "date", "label": "Logseq Scheduled"},
        DEADLINE: {"type": "date", "label": "Logseq Deadline"},
        PAGE: {"type": "string", "label": "Logseq Page"},
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
        "Doing": "pending",
        "Todo": "pending",
        "In Review": "pending",
        "Backlog": "pending",
        "Done": "completed",
        "Canceled": "deleted",
    }

    # replace characters that cause escaping issues like [] and "
    # this is a workaround for https://github.com/ralphbean/taskw/issues/172
    def _unescape_content(self, content):
        return (
            content.replace('"', "'")  # prevent &dquote; in task details
            .replace(
                "[[", self.config.char_open_link
            )  # alternate brackets for linked items
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
    def get_formatted_title(self):
        # DB mode uses :block/title, classic mode uses content
        content = (
            self.record.get("block/title")
            or self.record.get(":block/title")
            or self.record.get("content", "")
        )

        if not content:
            return ""

        # use first line only and remove state and priority
        first_line = content.split("\n")[0]  # only use first line

        # Remove state marker if present
        state = self.get_logseq_state()
        if state and first_line.startswith(state + " "):
            first_line = first_line.split(state + " ", 1)[1]

        # Remove priority markers
        first_line = (
            first_line.replace("[#A] ", "").replace("[#B] ", "").replace("[#C] ", "")
        )

        return self._unescape_content(first_line)

    # get a list of tags from the task content
    def get_tags_from_content(self):
        # pattern match for #[[multi word]] tags and #single word tags
        # but ignore any non-tag use of the # character in URLs
        # like http://example.com/page#test or in `#code`
        # Regex Pattern: (?<=\s)(#【.*?】|#\S+)
        # Note that this is processed after the content is unescaped,
        # so we use the char_open_link and char_close_link
        tags = re.findall(
            r"(?<=\s)"
            + "(#"
            + self.config.char_open_link
            + r".*?"
            + self.config.char_close_link
            + r"|#\S+"
            + ")",
            self.get_formatted_title(),
        )
        # compress format to single words and strip leading `#`
        tags = [self._compress_tag_format(t).lstrip("#") for t in tags]
        return tags

    # get a list of annotations from the content
    def get_annotations_from_content(self):
        annotations = []
        scheduled_date = None
        deadline_date = None
        in_logbook = False

        # DB mode uses :block/title, classic mode uses content
        content = (
            self.record.get("block/title")
            or self.record.get(":block/title")
            or self.record.get("content", "")
        )

        if not content:
            return annotations, scheduled_date, deadline_date

        for line in content.split("\n"):
            # Ignore things which are only useful within Logseq
            if in_logbook:
                if line.startswith(":END:"):
                    in_logbook = False
                continue

            if line.startswith(":LOGBOOK:"):
                in_logbook = True
                continue

            if line.startswith("id::"):
                continue

            # handle special annotations
            if line.startswith("SCHEDULED: "):
                scheduled_date = self.get_scheduled_date(line)
            elif line.startswith("DEADLINE: "):
                deadline_date = self.get_scheduled_date(line)
            else:
                annotations.append(self._unescape_content(line))

        if annotations:
            annotations.pop(0)  # remove first line
        return annotations, scheduled_date, deadline_date

    def get_url(self):
        return f'logseq://graph/{self.extra["graph"]}?block-id={self.record["uuid"]}'

    def get_logseq_state(self):
        # Handle both classic mode (marker attribute) and DB mode (property reference)
        if "marker" in self.record and self.record["marker"]:
            return self.record["marker"]
        elif ":logseq.property/status" in self.record:
            # DB mode: status is a reference with :block/title
            status_ref = self.record[":logseq.property/status"]
            if isinstance(status_ref, dict):
                # The pull pattern includes :block/title from the status entity
                return status_ref.get(
                    "block/title", status_ref.get(":block/title", "Todo")
                )
            elif isinstance(status_ref, str):
                return status_ref

        # Fallback
        log.warning(
            f"Could not determine task state for block {self.record.get('uuid', 'unknown')}"
        )
        return "TODO"

    def get_scheduled_date(self, scheduled):
        # format is <YYYY-MO-DD DAY HH:MM .+1d>
        # e.g. <2024-06-20 Thu 10:55 .+1d>
        date_split = (
            scheduled.replace("DEADLINE: <", "")
            .replace("SCHEDULED: <", "")
            .replace(">", "")
            .strip()
            .split(" ")
        )
        if len(date_split) == 2:  # <date day>
            date = date_split[0]
            date_format = "%Y-%m-%d"
        elif len(date_split) == 3 and (
            date_split[2][0] in ("+", ".")
        ):  # <date day repeat>
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

    def get_priority(self):
        """Extract priority from Logseq task content."""
        content = (
            self.record.get("block/title")
            or self.record.get(":block/title")
            or self.record.get("content", "")
        )

        # Check for [#A], [#B], [#C] markers in content
        if "[#A]" in content:
            return "H"
        elif "[#B]" in content:
            return "M"
        elif "[#C]" in content:
            return "L"
        else:
            return None  # No priority

    def to_taskwarrior(self):
        annotations, scheduled_date, deadline_date = self.get_annotations_from_content()
        wait_date = min(
            [d for d in [scheduled_date, deadline_date, self.SOMEDAY] if d is not None]
        )

        # Check for custom project property - it's stored directly in the record
        project = None

        # Look for any key that contains "project" in its name
        for key in self.record.keys():
            if "project" in str(key).lower():
                log.info(
                    f"Found key with 'project': {key}, value: {self.record[key]}, type: {type(self.record[key])}"
                )
                if key.startswith(":user.property/"):
                    project_value = self.record[key]
                    # The value might be a dict with db/id or a string
                    if isinstance(project_value, str):
                        project = project_value
                        log.info(f"Using project: {project}")
                        break
                    else:
                        log.info(f"Project value is not a string: {project_value}")

        # Fall back to graph name if no project property found
        if not project:
            project = self.extra["graph"]
            log.info(f"No project property found, using graph name: {project}")

        return {
            "project": project,
            "priority": self.get_priority(),
            "annotations": annotations,
            "tags": self.get_tags_from_labels(self.get_tags_from_content()),
            "due": deadline_date,
            "scheduled": scheduled_date,
            "wait": wait_date if self._is_waiting() else None,
            "status": self.STATE_MAP[self.get_logseq_state()],
            self.ID: self.record["id"],
            self.UUID: self.record["uuid"],
            self.STATE: self.get_logseq_state(),
            self.TITLE: self.get_formatted_title(),
            self.URI: self.get_url(),
            self.SCHEDULED: scheduled_date,
            self.DEADLINE: deadline_date,
            self.PAGE: self.extra["page_title"],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.get_formatted_title(),
            url=self.get_url() if self.config.inline_links else "",
            number=self.record["id"],
            cls="task",
        )


class LogseqService(Service):
    ISSUE_CLASS = LogseqIssue
    CONFIG_SCHEMA = LogseqConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = self.get_secret("token")
        filter = '"' + '" "'.join(self.config.task_state) + '"'
        self.client = LogseqClient(
            host=self.config.host,
            port=self.config.port,
            token=self.token,
            filter=filter,
        )

    @staticmethod
    def get_keyring_service(config):
        return f"http://{config.host}:{config.port}"

    def issues(self):
        graph_name = self.client.get_graph_name()
        for issue in self.client.get_issues():
            parent_page = self.client.get_page(issue[0]["parent"]["id"])
            extra = {"graph": graph_name, "page_title": parent_page.get("name")}
            yield self.get_issue_for_record(issue[0], extra)
