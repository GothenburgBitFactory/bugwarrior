from datetime import datetime
import logging
import re
import typing
import requests

from bugwarrior import config
from bugwarrior.services import Client, Issue, Service

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
        self.base_url = f"http://{host}:{port}/api"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "content-type": "application/json; charset=utf-8",
        }

    def _api_call(self, method, args):
        """Generic API call handler with error handling."""
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={"method": method, "args": args},
            )
            log.debug(f"API call to {method}: status {response.status_code}")
            return self.json_response(response)
        except requests.exceptions.ConnectionError as ce:
            log.fatal("Unable to connect to Logseq HTTP APIs server. %s", ce)
            exit(1)

    def _datascript_query(self, query):
        log.debug(f"DataScript query: {query}")
        return self._api_call("logseq.DB.datascriptQuery", [query])

    def _get_current_graph(self):
        return self._api_call("logseq.App.getCurrentGraph", [])

    def get_graph_name(self):
        graph = self._get_current_graph()
        if not graph:
            return None

        # Try to get the path/display name first, fall back to name
        #        name = graph.get("path") or graph.get("name")
        name = graph.get("name")

        # Strip "logseq_db_" prefix if present
        if name and name.startswith("logseq_db_"):
            name = name.replace("logseq_db_", "")

        return name

    def get_page(self, page_id):
        return self._api_call("logseq.Editor.getPage", [page_id])

    def get_issues(self):
        log.info("Querying Logseq DB 0.11.0+ (DB mode)")
        filter_set = f"#{{{self.filter}}}"

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
    # Field constants
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

    # map A B C priority to H M L
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

    def _get_content_field(self, *field_names):
        """Helper to get the first available content field from various possible keys."""
        for field in field_names:
            value = self.record.get(field)
            if value:
                return value
        return ""

    def _unescape_content(self, content):
        """Escape special characters for taskwarrior compatibility."""
        return (
            content.replace('"', "'")
            .replace("[[", self.config.char_open_link)
            .replace("]]", self.config.char_close_link)
            .replace("[", self.config.char_open_bracket)
            .replace("]", self.config.char_close_bracket)
        )

    def _compress_tag_format(self, tag):
        """Remove special characters from tags."""
        return (
            tag.replace(self.config.char_open_link, "")
            .replace(" ", "")
            .replace(self.config.char_close_link, "")
        )

    def _resolve_references_in_title(self, title):
        """Resolve UUID references in title to actual page names."""
        log.debug(f"Resolving references in title: {title}")

        # Pattern to match [[uuid]] references
        uuid_pattern = (
            r"\[\[([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\]\]"
        )

        def replace_uuid(match):
            uuid = match.group(1)
            log.debug(f"Found UUID reference: {uuid}")
            try:
                # Query for the block/page with this UUID
                query = f'[:find (pull ?e [:block/title :block/name :block/original-name]) :where [?e :block/uuid #uuid "{uuid}"]]'
                log.debug(f"Running query: {query}")
                result = self.extra["client"]._datascript_query(query)
                log.debug(f"Query result: {result}")

                if result and result[0]:
                    entity = result[0][0]
                    log.debug(f"Entity found: {entity}")
                    # Try to get the readable name (try both with and without "block/" prefix)
                    name = (
                        entity.get("block/original-name")
                        or entity.get("original-name")
                        or entity.get("block/name")
                        or entity.get("name")
                        or entity.get("block/title")
                        or entity.get("title")
                        or uuid
                    )
                    log.debug(f"Resolved UUID {uuid} to name: {name}")
                    return f"[[{name}]]"
                else:
                    log.warning(f"No entity found for UUID {uuid}")
            except Exception as e:
                log.warning(f"Failed to resolve UUID reference {uuid}: {e}")

            return match.group(0)  # Return original if resolution fails

        result = re.sub(uuid_pattern, replace_uuid, title, flags=re.IGNORECASE)
        log.debug(f"Title after resolution: {result}")
        return result

    def get_logseq_state(self):
        """Extract the task state from either classic or DB mode."""
        # Classic mode
        if "marker" in self.record and self.record["marker"]:
            return self.record["marker"]

        # DB mode
        if ":logseq.property/status" in self.record:
            status_ref = self.record[":logseq.property/status"]
            if isinstance(status_ref, dict):
                return status_ref.get(
                    "block/title", status_ref.get(":block/title", "Todo")
                )
            elif isinstance(status_ref, str):
                return status_ref

        return "TODO"

    def get_formatted_title(self):
        """Get the task title with state markers and priority removed."""
        content = self._get_content_field("full-title", "title", "content")
        if not content:
            return ""

        first_line = content.split("\n")[0]

        # Remove state marker
        state = self.get_logseq_state()
        if state and first_line.startswith(f"{state} "):
            first_line = first_line.split(f"{state} ", 1)[1]

        # Remove priority markers
        for priority in ["[#A]", "[#B]", "[#C]"]:
            first_line = first_line.replace(f"{priority} ", "")

        # Resolve UUID references to actual page names
        first_line = self._resolve_references_in_title(first_line)

        return self._unescape_content(first_line)

    def get_tags_from_content(self):
        """Extract hashtags from content."""
        pattern = (
            r"(?<=\s)(#"
            + self.config.char_open_link
            + r".*?"
            + self.config.char_close_link
            + r"|#\S+)"
        )
        tags = re.findall(pattern, self.get_formatted_title())
        return [self._compress_tag_format(t).lstrip("#") for t in tags]

    def get_deadline_date(self):
        """Extract deadline from DB mode property or classic mode content."""
        # DB mode: check for :logseq.property/deadline timestamp
        deadline_ts = self.record.get(":logseq.property/deadline")
        if deadline_ts:
            try:
                # Convert from milliseconds to seconds
                return datetime.fromtimestamp(deadline_ts / 1000)
            except (ValueError, TypeError) as e:
                log.warning(f"Could not parse deadline timestamp {deadline_ts}: {e}")

        # Fallback to classic mode parsing from content
        content = self._get_content_field("block/title", ":block/title", "content")
        if not content:
            return None

        for line in content.split("\n"):
            if line.startswith("DEADLINE: "):
                return self._parse_date_line(line)

        return None

    def get_scheduled_date(self):
        """Extract scheduled date from DB mode property or classic mode content."""
        # DB mode: check for :logseq.property/scheduled timestamp
        scheduled_ts = self.record.get(":logseq.property/scheduled")
        if scheduled_ts:
            try:
                # Convert from milliseconds to seconds
                return datetime.fromtimestamp(scheduled_ts / 1000)
            except (ValueError, TypeError) as e:
                log.warning(f"Could not parse scheduled timestamp {scheduled_ts}: {e}")

        # Fallback to classic mode parsing from content
        content = self._get_content_field("block/title", ":block/title", "content")
        if not content:
            return None

        for line in content.split("\n"):
            if line.startswith("SCHEDULED: "):
                return self._parse_date_line(line)

        return None

    def get_annotations_from_content(self):
        """Parse annotations from block content (excluding dates handled separately)."""
        annotations = []
        in_logbook = False

        content = self._get_content_field("block/title", ":block/title", "content")
        if not content:
            return annotations

        for line in content.split("\n"):
            if line.startswith(":LOGBOOK:"):
                in_logbook = True
                continue
            if line.startswith(":END:"):
                in_logbook = False
                continue
            if in_logbook or line.startswith("id::"):
                continue

            # Skip SCHEDULED/DEADLINE lines (handled by separate methods)
            if line.startswith("SCHEDULED: ") or line.startswith("DEADLINE: "):
                continue

            annotations.append(self._unescape_content(line))

        # Remove first line (the title itself)
        if annotations:
            annotations.pop(0)

        return annotations

    def _parse_date_line(self, line):
        """Parse SCHEDULED or DEADLINE date lines."""
        date_str = (
            line.replace("DEADLINE: <", "")
            .replace("SCHEDULED: <", "")
            .replace(">", "")
            .strip()
        )
        date_parts = date_str.split(" ")

        date_formats = [
            (2, "%Y-%m-%d", lambda p: p[0]),
            (
                3,
                "%Y-%m-%d",
                lambda p: p[0] if p[2][0] in ("+", ".") else f"{p[0]} {p[2]}",
            ),
            (3, "%Y-%m-%d %H:%M", lambda p: f"{p[0]} {p[2]}"),
            (4, "%Y-%m-%d %H:%M", lambda p: f"{p[0]} {p[2]}"),
        ]

        for expected_len, date_format, extractor in date_formats:
            if len(date_parts) == expected_len:
                try:
                    date_str = extractor(date_parts)
                    if date_format == "%Y-%m-%d" and " " in date_str:
                        date_format = "%Y-%m-%d %H:%M"
                    return datetime.strptime(date_str, date_format)
                except (ValueError, IndexError):
                    continue

        log.warning(f"Could not parse date from line: {line}")
        return None

    def get_priority(self):
        """Extract priority from content."""
        content = self._get_content_field("block/title", ":block/title", "content")

        for marker, priority in [("[#A]", "H"), ("[#B]", "M"), ("[#C]", "L")]:
            if marker in content:
                return priority
        return None

    def get_url(self):
        """Generate logseq:// URL for the block."""
        return f'logseq://graph/{self.extra["graph"]}?block-id={self.record["uuid"]}'

    def _is_waiting(self):
        """Check if task is in a waiting state."""
        return self.get_logseq_state() in ["WAIT", "WAITING"]

    def _is_journal_date(self, text):
        """Check if text is a journal date (YYYY-MM-DD)."""
        try:
            datetime.strptime(str(text), "%Y-%m-%d")
            return True
        except (ValueError, TypeError):
            return False

    def _find_project_property_ref(self):
        """Locate the project property within nested or top-level keys."""
        # Check nested properties (legacy/mixed mode)
        props = (
            self.record.get("block/properties")
            or self.record.get(":block/properties")
            or self.record.get("properties")
        )

        if props and isinstance(props, dict):
            for key, value in props.items():
                if "project" in str(key).lower():
                    log.debug(f"Found project in nested props: {key} -> {value}")
                    return value

        # Check top-level keys (DB 0.11.0+)
        for key, value in self.record.items():
            key_str = str(key).lower()
            if "project" in key_str and (
                key_str in ("project", ":project") or "/project" in key_str
            ):
                log.debug(f"Found project at top level: {key} -> {value}")
                return value

        return None

    def _resolve_project_name(self, project_ref):
        """Resolve a project reference (ID, dict, or string) to a readable name."""
        if not project_ref:
            return None

        # Direct string value
        if isinstance(project_ref, str):
            return project_ref

        # Extract reference ID
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
            # Try DataScript query first
            query = f"[:find (pull ?e [*]) :where [?e :db/id {ref_id}]]"
            result = self.extra["client"]._datascript_query(query)

            entity = result[0][0] if result and result[0] else None

            # Fallback to getPage API
            if not entity:
                entity = self.extra["client"].get_page(ref_id)

            if entity:
                # Try various name fields
                name_fields = [
                    "block/original-name",
                    "block/name",
                    "block/title",
                    "original-name",
                    "name",
                    "title",
                    "block/content",
                    "content",
                ]

                for field in name_fields:
                    resolved = entity.get(field)
                    if resolved:
                        # Skip journal dates
                        if self._is_journal_date(resolved):
                            log.debug(f"Ignoring journal date as project: {resolved}")
                            return None
                        return resolved

        except Exception as e:
            log.warning(f"Failed to resolve project reference {ref_id}: {e}")

        return None

    def _determine_project(self):
        """Determine the project for this task with fallbacks."""
        # 1. Try explicit project property
        project_ref = self._find_project_property_ref()
        project = self._resolve_project_name(project_ref)

        if project:
            log.debug(f"Using project from property: {project}")
            return project

        # 2. Fall back to parent page title (if not a journal date)
        page_title = self.extra.get("page_title")
        if page_title and not self._is_journal_date(page_title):
            log.debug(f"Using parent page as project: {page_title}")
            return page_title

        # 3. Fall back to graph name
        graph = self.extra.get("graph")
        log.debug(f"Using graph name as project: {graph}")
        return graph

    def to_taskwarrior(self):
        """Convert Logseq task to taskwarrior format."""
        log.debug(f"Converting task {self.record.get('uuid')}")

        # Get dates from DB mode properties or classic mode content
        scheduled_date = self.get_scheduled_date()
        deadline_date = self.get_deadline_date()
        annotations = self.get_annotations_from_content()

        # Calculate wait date (earliest of scheduled/deadline, or SOMEDAY)
        wait_date = min(
            d for d in [scheduled_date, deadline_date, self.SOMEDAY] if d is not None
        )

        # Determine project with clean fallback logic
        project = self._determine_project()
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
        """Build the default description for taskwarrior."""
        return self.build_default_description(
            title=self.get_formatted_title(),
            url=self.get_url() if self.config.inline_links else "",
            number=self.record["id"],
            cls="task",
        )


class LogseqService(Service):
    API_VERSION = 1.0
    ISSUE_CLASS = LogseqIssue
    CONFIG_SCHEMA = LogseqConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = self.get_secret("token")
        filter_string = '"' + '" "'.join(self.config.task_state) + '"'
        self.client = LogseqClient(
            host=self.config.host,
            port=self.config.port,
            token=self.token,
            filter=filter_string,
        )

    @staticmethod
    def get_keyring_service(config):
        return f"http://{config.host}:{config.port}"

    def issues(self):
        """Generate issues from Logseq."""
        graph_name = self.client.get_graph_name()

        for issue in self.client.get_issues():
            parent_page = self.client.get_page(issue[0]["parent"]["id"])
            extra = {
                "graph": graph_name,
                "page_title": parent_page.get("name") if parent_page else None,
                "client": self.client,
            }
            yield self.get_issue_for_record(issue[0], extra)
