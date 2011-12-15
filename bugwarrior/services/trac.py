
from bugwarrior.services import IssueService
from bugwarrior.config import die


class TracService(IssueService):
    def __init__(self, *args, **kw):
        super(TracService, self).__init__(*args, **kw)

    @classmethod
    def validate_config(cls, config, target):
        if not config.has_option(target, 'url'):
            die("[%s] has no 'url'" % target)

        # TODO -- validate other options

        IssueService.validate_config(config, target)
