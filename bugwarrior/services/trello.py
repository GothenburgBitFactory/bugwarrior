from bugwarrior.services import IssueService, Issue
from bugwarrior.config import die


class TrelloService(IssueService):
    @classmethod
    def validate_config(cls, config, target):
        if not config.has_option(target, 'trello.token'):
            die("[%s] has no 'trello.token'" % target)

        if not config.has_option(target, 'trello.api_key'):
            die("[%s] has no 'trello.api_key'" % target)

        super(TrelloService, cls).validate_config(config, target)
