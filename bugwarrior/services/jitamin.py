from array import array
import requests
import logging
import typing_extensions
import pydantic

from bs4 import BeautifulSoup

from bugwarrior import config
from bugwarrior.services import IssueService, Issue

log = logging.getLogger(__name__)


### Temporary stuff START

# will move this to a new project.


class Jitamin:
    pass


class Task:
    def __init__(self, instance: Jitamin, url: pydantic.AnyHttpUrl, data: dict) -> None:
        self._instance = instance
        self._url = url
        self._data = data
        # We are trying to live with the data given to us for as long as possible
        self._fetched_task = False

    def url(self) -> str:
        return self._url

    def get(self, attribute, default=None):
        if not self._fetched_task and not attribute in self._data.keys():
            log.debug(
                "Fetching info for task %s, because %s was queried",
                self._url,
                attribute,
            )
            # could not work with the data given. need to query the task overview page
            self.fetch_data()
        try:
            return self._data[attribute]
        except KeyError:
            return default

    def fetch_data(self) -> None:
        response = self._instance.session.get(self._url)

        soup = BeautifulSoup(response.content, "html.parser")

        self._data["title"] = soup.find("h2").text.strip()

        # page title is PROJECTNAME, #NUMBER - Title - INSTANCENAME
        project = soup.find("title").text.strip()
        project = project[: project.find(",")]
        self._data["project"] = project

        for listitem in soup.find_all("li"):
            text = listitem.text.strip()
            for identifer in [
                "Status",
                "Progress",
                "Priority",
                "Reference",
                "Complexity",
                "Category",
                "Swimlane",
                "Column",
                "Position",
                "Assignee",
                "Creator",
                "Due date",
                "Time estimated",
                "Time spent",
                "Created",
                "Modified",
                "Completed",
                "Started",
                "Moved",
            ]:
                if text.startswith(identifer):
                    value = text[text.find(":") + 1 :].strip()
                    self._data[identifer.lower().replace(" ", "_")] = value

        self._data["tags"] = []

        tag_cloud = soup.find("div", attrs={"class": "task-tags"})
        if tag_cloud is not None:
            for tag in tag_cloud.find_all("li"):
                self._data["tags"].append(tag.text.strip())

        self._data["comments"] = []
        for comment in soup.find_all("div", attrs={"class": "comment"}):
            user = comment.find(
                "strong", attrs={"class": "comment-username"}
            ).text.strip()
            content = (
                comment.find("div", attrs={"class": "comment-content"})
                .text.strip()
                .replace("\n", " ")
            )
            self._data["comments"].append((user, content))

        self._data["description"] = ""

        for headline in soup.find_all("h3"):
            if "Description" in headline.text:
                self._data["description"] = soup.find(
                    "div", attrs={"class": "accordion-content"}
                ).text.strip()

        self._fetched_task = True


class Jitamin:
    def __init__(
        self,
        url: pydantic.AnyHttpUrl,
        username: str,
        password: str,
        verify_ssl: bool = True,
    ):
        self.session = requests.session()
        self.base_uri = url

        if not verify_ssl:
            self.session.verify = False
            requests.packages.urllib3.disable_warnings()

        response = self.session.get(self.base_uri + "/check")
        if response.headers.get("Location") is None:
            log.info("Logging into %s", self.base_uri)
            soup = BeautifulSoup(response.content, "html.parser")
            token = soup.find("input", attrs={"name": "csrf_token"})
            if token is not None:
                token = token.get("value")

            response = self.session.post(
                self.base_uri + "/check",
                data={
                    "username": username,
                    "password": password,
                    "remember_me": "1",
                    "csrf_token": token,
                },
            )

            soup = BeautifulSoup(response.content, "html.parser")
            error = soup.find("p", attrs={"class": "alert alert-error"})

            if error is not None:
                raise ValueError(error.text)

    def search(self, query: str):
        # jitamin does not like empty queries
        if query is None or len(query) == 0:
            query = "created:>1970-01-01"
        i = 1
        while True:
            tasklist = self._get_task_list_page(
                "?controller=SearchController&action=index&q="
                + query
                + "&order=tasks.id&direction=DESC&page="
                + str(i)
            )
            i = i + 1

            if len(tasklist) == 0:
                break

            for task in tasklist:
                yield task

    def _get_task_list_page(self, url) -> array:
        response = self.session.get(self.base_uri + url)

        soup = BeautifulSoup(response.content, "html.parser")
        tasklist = []
        for entry in soup.find_all("tr"):
            number = entry.td
            # the first table row has no entries
            if number is None:
                continue
            task_url = number.a["href"]
            entries = [
                "number",
                "project",
                "swimlane",
                "column",
                "category",
                "title",
                "assignee",
                "due_date",
                "status",
            ]
            data = {}
            for name, child in zip(entries, entry.find_all("td")):
                temp = child.text.strip()
                if len(temp) > 0:
                    data[name] = temp
            tasklist.append(Task(self, self.base_uri + task_url, data))
        return tasklist


### Temporary stuff END


class JitaminConfig(config.ServiceConfig, prefix="jitamin"):
    service: typing_extensions.Literal["jitamin"]
    base_uri: pydantic.AnyHttpUrl
    username: str
    password: str

    verify_ssl: bool = True
    column_as_tag: bool = False

    query: str = "status:open"


class JitaminIssue(Issue):
    URL = "jitaminurl"
    POSITION = "jitaminposition"
    COLUMN = "jitamincolumn"
    DESCRIPTION = "jitamindescription"

    UDAS = {
        URL: {
            'type': 'string',
            'label': 'Jitamin URL',
        },
        POSITION: {
            'type': 'string',
            'label': 'Jitamin Position in order',
        },
        COLUMN: {
            'type': 'string',
            'label': 'Jitamin Column',
        },
        DESCRIPTION: {
            'type': 'string',
            'label': 'Jitamin Description',
        },
    }
    UNIQUE_KEY = (URL,)

    # jitamin has 4 mandatory priorities, Taskwarrior has 3 optional priorities.
    # Map the three higher prio to taskwarriors priorities and ignore the
    # default lowest priority
    PRIORITY_MAP = {"P3": "H", "P2": "M", "P1": "L", "P0": ""}

    def to_taskwarrior(self):
        created = self.parse_date(self.record.get("created"))
        due = self.parse_date(self.record.get("due"))

        tags = self.record.get("tags")
        if self.extra["config"].column_as_tag and self.record.get("column") is not None:
            tags.append(self.record.get("column"))

        return {
            "project": self.record.get("project"),
            "annotations": self.extra["annotations"],  # comments
            "priority": self.get_priority(),
            "tags": tags,
            "due": due,
            "entry": created,
            self.URL: self.extra["url"],
            self.POSITION: self.record.get("position"),
            self.COLUMN: self.record.get("column"),
            self.DESCRIPTION: self.record.get("description"),
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.record.get("title"),
            url=self.get_processed_url(self.extra["url"]),
            cls="task",
            number=self.record.get("number").replace("#", ""),
        )


class JitaminService(IssueService):
    ISSUE_CLASS = JitaminIssue
    CONFIG_SCHEMA = JitaminConfig

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.jitamin = Jitamin(
            self.config.base_uri,
            self.config.username,
            self.get_password("password", self.config.username),
            self.config.verify_ssl,
        )

    @staticmethod
    def get_keyring_service(config):
        return f"jitamin://{config.base_uri}"

    def get_service_metadata(self):
        return {"url": self.config.base_uri}

    def get_owner(self, issue):
        assignee = issue.get("assignee")
        # translate between Jitamin unassigned and bugwarrior unassigned
        if assignee == "Unassigned":
            return None
        # assignee is not a username, but "last_name, first_name"
        # so we make it more "usernamelike"
        if assignee is not None:
            return assignee.replace(",", "").replace(" ", "_")

    def include(self, issue):
        # filter out closed tasks, as bugwarrior, will close all tasks not present anymore
        if issue.get("status") == "closed":
            return False
        return super().include(issue)

    def issues(self):
        tasks = self.jitamin.search(self.config.query)
        tasks = filter(self.include, tasks)

        for issue in tasks:

            extra = {
                "url": issue.url(),
                "project": issue.get("project"),
                "type": "task",
                "config": self.config,
                "annotations": self.build_annotations(
                    issue.get("comments"), issue.url()
                ),
            }
            yield self.get_issue_for_record(issue, extra)
