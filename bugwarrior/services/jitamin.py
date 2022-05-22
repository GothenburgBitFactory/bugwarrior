import requests
import logging
import typing_extensions
import pydantic

from bs4 import BeautifulSoup

from bugwarrior import config
from bugwarrior.services import IssueService, Issue

log = logging.getLogger(__name__)

class JitaminConfig(config.ServiceConfig, prefix="jitamin"):
    service: typing_extensions.Literal["jitamin"]
    base_uri: pydantic.AnyHttpUrl
    username: str
    password: str

    verify_ssl: bool = True
    column_as_tag: bool = False

    query: str = ""


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
    # Map the thre higher prio to taskwarriors priorities and skipt the default
    # lowest priority
    PRIORITY_MAP = {"P3": "H", "P2": "M", "P1": "L", "P0": ""}

    def to_taskwarrior(self):
        created = self.parse_date(self.record.get("created"))
        due = self.parse_date(self.record.get("due"))
        return {
            "project": self.record["project"],
            "annotations": self.extra["annotations"],  # comments
            "priority": self.get_priority(),
            "tags": self.record.get("tags"),
            "due": due,
            "entry": created,
            self.URL: self.extra["url"],
            self.POSITION: self.record["position"],
            self.COLUMN: self.record["column"],
            self.DESCRIPTION: self.record["description"],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.record["title"],
            url=self.get_processed_url(self.extra["url"]),
            cls="task",
            number=self.extra["url"].split("/")[-1]
        )


class JitaminService(IssueService):
    ISSUE_CLASS = JitaminIssue
    CONFIG_SCHEMA = JitaminConfig

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.password = self.get_password("password", self.config.username)
        self.session = requests.session()

        if not self.config.verify_ssl:
            self.session.verify = False
            requests.packages.urllib3.disable_warnings()

        response = self.session.get(self.config.base_uri + "/check")
        if response.headers.get("Location") is None:
            log.info("Logging into %s", self.config.base_uri)
            soup = BeautifulSoup(response.content, "html.parser")
            token = soup.find("input", attrs={"name": "csrf_token"})
            if token is not None:
                token = token.get("value")

            response = self.session.post(
                self.config.base_uri + "/check",
                data={
                    "username": self.config.username,
                    "password": self.password,
                    "remember_me": "1",
                    "csrf_token": token,
                },
            )

            soup = BeautifulSoup(response.content, "html.parser")
            error = soup.find("p", attrs={"class": "alert alert-error"})

            if error is not None:
                raise ValueError(error.text)

    @staticmethod
    def get_keyring_service(config):
        return f"jitamin://{config.base_uri}"

    def get_service_metadata(self):
        return {"url": self.config.base_uri}

    def get_owner(self, issue):
        if issue['assignee'] is not None:
            return issue['assignee'].replace(",","").replace(" ", "_")

    def issues(self):
        for link in self.get_task_list():
            issue = self.get_single_task(link)

            if issue is None:
                continue

            extra = {
                "url": self.config.base_uri + link,
                "project": issue["project"],
                "type": "task",
                "annotations": self.build_annotations(
                    issue["comments"], self.config.base_uri + link
                ),
            }
            yield self.get_issue_for_record(issue, extra)

    def get_task_list_page(self, url):
        response = self.session.get(self.config.base_uri + url)

        soup = BeautifulSoup(response.content, "html.parser")

        link_list = []

        for link_tag in soup.find_all("a"):
            link = link_tag.get("href")
            if link is None:
                continue
            if not "/task/" in link:
                continue
            if len(link.split("/")) != 5:
                continue
            if link in link_list:
                continue
            link_list.append(link)
        return link_list

    def get_task_list(self):
        i = 1
        while True:
            tasklist = self.get_task_list_page(
                "?controller=SearchController&action=index&q="
                + self.config.query + " status:open"
                + "&order=tasks.id&direction=DESC&page="
                + str(i)
            )
            i = i + 1

            if len(tasklist) == 0:
                break

            for task in tasklist:
                yield task

    def get_single_task(self, url):
        response = self.session.get(self.config.base_uri + url)

        soup = BeautifulSoup(response.content, "html.parser")

        task = {}

        task["title"] = soup.find("h2").text.strip()

        project = soup.find("title").text.strip()
        project = project[: project.find(",")]
        task["project"] = project

        for listitem in soup.find_all("li"):
            text = listitem.text.strip()
            for identifer in [
                "Status",
                "Created",
                "Due",
                "Column",
                "Priority",
                "Position",
                "Creator",
                "Assignee",
            ]:
                if text.startswith(identifer):
                    value = text[text.find(":") + 1 :].strip()
                    task[identifer.lower()] = value

        # skip closed tasks bugwarrior will close for us
        if task["status"] == "closed":
            return

        task["tags"] = []

        if self.config.column_as_tag and task["column"] is not None:
            task["tags"].append(task["column"])

        tag_cloud = soup.find("div", attrs={"class": "task-tags"})
        if tag_cloud is not None:
            for tag in tag_cloud.find_all("li"):
                task["tags"].append(tag.text.strip())

        task["comments"] = []
        for comment in soup.find_all("div", attrs={"class": "comment"}):
            user = comment.find("strong", attrs={"class": "comment-username"}).text.strip()
            content = (
                comment.find("div", attrs={"class": "comment-content"})
                .text.strip()
                .replace("\n", " ")
            )
            task["comments"].append((user, content))

        task["description"] = ""

        for headline in soup.find_all("h3"):
            if "Description" in headline.text:
                task["description"] = soup.find(
                    "div", attrs={"class": "accordion-content"}
                ).text.strip()

        return task
