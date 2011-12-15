
from bugwarrior.services import IssueService
from bugwarrior.config import die


class BitbucketService(IssueService):
    def __init__(self, *args, **kw):
        super(BitbucketService, self).__init__(*args, **kw)

    @classmethod
    def validate_config(cls, config, target):
        if not config.has_option(target, 'username'):
            die("[%s] has no 'username'" % target)

        # TODO -- validate other options

        IssueService.validate_config(config, target)
