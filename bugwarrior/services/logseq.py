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
            log.debug(f"Query: {query}")
            response = requests.post(
                f"http://{self.host}:{self.port}/api",
                headers=self.headers,
                json={"method": "logseq.DB.datascriptQuery", "args": [query]},
            )
            log.debug(f"Response status: {response.status_code}, body: {response.text}")
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
        print("DEBUG: Using modified logseq.py for DB 0.11.0 (Refactored)")

        filter_set = f"#{{{self.filter}}}"

        # DB Mode Query
        query = f"""
            [:find (pull ?b [* :block/full-title {{:logseq.property/status [:block/title]}}])
            :where
            [?b :block/uuid _]
            (or-join [?b]
                ;; Classic mode
                (and
                [?b :block/marker ?marker]
                [(contains? {filter_set} ?marker)]
                )
                ;; DB mode status
                (and
                [?b :logseq.property/status ?status-ref]
                [?status-ref :block/title ?status-name]
                [(contains? {filter_set} ?status-name)]
                )
            )
            ]
        """

        result = self._datascript_query(query)
        if "error" in result:
            log.fatal("Error querying Logseq: %s", result["error"])
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
    SOMEDAY = datetime(2038, 1, 18)

    UDAS = {
        ID: {"type": "string", "label": "Logseq ID"},
        UUID: {"type": "string", "label": "Logseq UUID"},
        STATE: {"type": "string", "label": "Logseq State"},
        TITLE: {"type": "string", "label": "Logseq Title"},
        DONE: {"type": "date", "label": "Logseq Done"},
        URI: {"type": "string", "label": "Logseq URI"},
        SCHEDULED: {"type": "date", "label": "Logseq Scheduled"},
        DEADLINE: {"type": "date", "label": "Logseq Deadline"},
        PAGE: {"type": "string", "label": "Logseq Page"},
    }

    UNIQUE_KEY = (ID, UUID)

    PRIORITY_MAP = {"A": "H", "B": "M", "C": "L"}

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

    def _unescape_content(self, content):
        return (
            content.replace('"', "'")
            .replace("[[", self.config.char_open_link)
            .replace("]]", self.config.char_close_link)
            .replace("[", self.config.char_open_bracket)
            .replace("]", self.config.char_close_bracket)
        )

    def _compress_tag_format(self, tag):
        return (
            tag.replace(self.config.char_open_link, "")
            .replace(" ", "")
            .replace(self.config.char_close_link, "")
        )

    def get_formatted_title(self):
        content = (
            self.record.get("full-title")
            or self.record.get("title")
            or self.record.get("content", "")
        )

        if not content:
            return ""

        first_line = content.split("\n")[0]
        state = self.get_logseq_state()
        if state and first_line.startswith(state + " "):
            first_line = first_line.split(state + " ", 1)[1]

        first_line = (
            first_line.replace("[#A] ", "").replace("[#B] ", "").replace("[#C] ", "")
        )

        return self._unescape_content(first_line)

    def get_tags_from_content(self):
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
        tags = [self._compress_tag_format(t).lstrip("#") for t in tags]
        return tags

    def get_annotations_from_content(self):
        annotations = []
        scheduled_date = None
        deadline_date = None
        in_logbook = False

        content = (
            self.record.get("block/title")
            or self.record.get(":block/title")
            or self.record.get("content", "")
        )

        if not content:
            return annotations, scheduled_date, deadline_date

        for line in content.split("\n"):
            if in_logbook:
                if line.startswith(":END:"):
                    in_logbook = False
                continue
            if line.startswith(":LOGBOOK:"):
                in_logbook = True
                continue
            if line.startswith("id::"):
                continue
            if line.startswith("SCHEDULED: "):
                scheduled_date = self.get_scheduled_date(line)
            elif line.startswith("DEADLINE: "):
                deadline_date = self.get_scheduled_date(line)
            else:
                annotations.append(self._unescape_content(line))

        if annotations:
            annotations.pop(0)
        return annotations, scheduled_date, deadline_date

    def get_url(self):
        return f'logseq://graph/{self.extra["graph"]}?block-id={self.record["uuid"]}'

    def get_logseq_state(self):
        if "marker" in self.record and self.record["marker"]:
            return self.record["marker"]
        elif ":logseq.property/status" in self.record:
            status_ref = self.record[":logseq.property/status"]
            if isinstance(status_ref, dict):
                return status_ref.get(
                    "block/title", status_ref.get(":block/title", "Todo")
                )
            elif isinstance(status_ref, str):
                return status_ref
        return "TODO"

    def get_scheduled_date(self, scheduled):
        date_split = (
            scheduled.replace("DEADLINE: <", "")
            .replace("SCHEDULED: <", "")
            .replace(">", "")
            .strip()
            .split(" ")
        )
        date = None
        date_format = None

        if len(date_split) == 2:
            date = date_split[0]
            date_format = "%Y-%m-%d"
        elif len(date_split) == 3 and (date_split[2][0] in ("+", ".")):
            date = date_split[0]
            date_format = "%Y-%m-%d"
        elif len(date_split) == 3:
            date = date_split[0] + " " + date_split[2]
            date_format = "%Y-%m-%d %H:%M"
        elif len(date_split) == 4:
            date = date_split[0] + " " + date_split[2]
            date_format = "%Y-%m-%d %H:%M"

        if date:
            try:
                return datetime.strptime(date, date_format)
            except ValueError:
                log.warning(f"Could not parse date {date}")
        return None

    def _is_waiting(self):
        return self.get_logseq_state() in ["WAIT", "WAITING"]

    def get_priority(self):
        content = (
            self.record.get("block/title")
            or self.record.get(":block/title")
            or self.record.get("content", "")
        )
        if "[#A]" in content:
            return "H"
        elif "[#B]" in content:
            return "M"
        elif "[#C]" in content:
            return "L"
        else:
            return None

    # --- Helper Methods to Reduce Complexity ---

    def _find_project_property_ref(self):
        """Locates the project property within nested or top-level keys."""
        # 1. Check Nested properties (Legacy/Mixed)
        props = (
            self.record.get("block/properties")
            or self.record.get(":block/properties")
            or self.record.get("properties")
        )

        if props and isinstance(props, dict):
            for k, v in props.items():
                if "project" in str(k).lower():
                    print(f"DEBUG: Found project in nested props: {k} -> {v}")
                    return v

        # 2. Check Top Level (DB 0.11.0+)
        for key, value in self.record.items():
            key_str = str(key).lower()
            if "project" in key_str:
                if (
                    key_str == "project"
                    or key_str == ":project"
                    or "/project" in key_str
                ):
                    print(f"DEBUG: Found project key at top level: {key} -> {value}")
                    return value
        return None

    def _resolve_project_name(self, project_ref):
        """Resolves a project reference (ID or String) to a human-readable name."""
        if not project_ref:
            return None

        # Handle Direct String
        if isinstance(project_ref, str):
            return project_ref

        # Handle Reference (Dict or Int)
        ref_id = None
        if isinstance(project_ref, dict):
            ref_id = (
                project_ref.get("db/id")
                or project_ref.get("id")
                or project_ref.get(":db/id")
            )
        elif isinstance(project_ref, int):
            ref_id = project_ref

        if not ref_id:
            return None

        try:
            # 1. Try DataScript with wildcard [*]
            project_query = f"[:find (pull ?e [*]) :where [?e :db/id {ref_id}]]"
            result = self.extra["client"]._datascript_query(project_query)

            entity = None
            if result and len(result) > 0 and result[0]:
                entity = result[0][0]

            # 2. Fallback to getPage API
            if not entity:
                entity = self.extra["client"].get_page(ref_id)

            if entity:
                resolved_project = (
                    entity.get("block/original-name")
                    or entity.get("block/name")
                    or entity.get("block/title")
                    or entity.get("original-name")
                    or entity.get("name")
                    or entity.get("title")
                    or entity.get("block/content")
                    or entity.get("content")
                )

                # Exclude Journal Dates
                try:
                    if resolved_project and datetime.strptime(
                        str(resolved_project), "%Y-%m-%d"
                    ):
                        log.info(
                            f"Resolved name '{resolved_project}' is a Journal Date. Ignoring."
                        )
                        return None
                except ValueError:
                    pass  # Not a date, this is good

                return resolved_project

        except Exception as e:
            log.warning(f"Failed to resolve project reference: {e}")

        return None

    def to_taskwarrior(self):
        # DEBUG PRINT
        print(f"DEBUG: Task {self.record.get('uuid')} Keys: {list(self.record.keys())}")

        annotations, scheduled_date, deadline_date = self.get_annotations_from_content()
        wait_date = min(
            [d for d in [scheduled_date, deadline_date, self.SOMEDAY] if d is not None]
        )

        # 1. Find and Resolve Project
        project_ref = self._find_project_property_ref()
        project = self._resolve_project_name(project_ref)

        # 2. Fallbacks
        if not project and self.extra.get("page_title"):
            parent_page_title = self.extra["page_title"]
            try:
                # Skip Journal Dates
                datetime.strptime(parent_page_title, "%Y-%m-%d")
            except ValueError:
                project = parent_page_title

        if not project:
            project = self.extra["graph"]

        # Final clean up
        if project and isinstance(project, str):
            project = project.replace("[[", "").replace("]]", "")

        return {
            "project": project,
            "priority": self.get_priority(),
            "annotations": annotations,
            "tags": self.get_tags_from_labels(self.get_tags_from_content()),
            "due": deadline_date,
            "scheduled": scheduled_date,
            "wait": wait_date if self._is_waiting() else None,
            "status": self.STATE_MAP.get(self.get_logseq_state(), "pending"),
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
            extra = {
                "graph": graph_name,
                "page_title": parent_page.get("name") if parent_page else None,
                "client": self.client,
            }
            yield self.get_issue_for_record(issue[0], extra)
