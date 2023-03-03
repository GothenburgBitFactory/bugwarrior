from dateutil.parser import parse as parse_date
import responses

from bugwarrior.services.trello import TrelloConfig, TrelloService, TrelloIssue
from bugwarrior.config.schema import MainSectionConfig

from .base import ConfigTest, ServiceTest


class TestTrelloIssue(ServiceTest):
    JSON = {
        "due": "2018-12-02T12:59:00.000Z",
        "id": "542bbb6583d705eb05bbe491",
        "idShort": 42,
        "name": "So long, and thanks for all the fish!",
        "shortLink": "AAaaBBbb",
        "shortUrl": "https://trello.com/c/AAaaBBbb",
        "url": "https://trello.com/c/AAaBBbb/42-so-long",
        "labels": [{'name': "foo"}, {"name": "bar"}],
        "desc": "some description",
    }

    def setUp(self):
        super().setUp()
        config = TrelloConfig(
            service='trello', api_key='abc123', token='def456',
            import_labels_as_tags=True, default_priority='M',
            label_template='trello_{{label}}')
        main_config = MainSectionConfig(
            interactive=False, targets=[], inline_links=True,
            description_length=31)
        extra = {'boardname': 'Hyperspatial express route',
                 'listname': 'Something'}
        self.issue = TrelloIssue(self.JSON, config, main_config, extra)

    def test_default_description(self):
        """ Test the generated description """
        expected_desc = "(bw)#42 - So long, and thanks for all the" \
                        " .. https://trello.com/c/AAaaBBbb"
        self.assertEqual(expected_desc, self.issue.get_default_description())

    def test_to_taskwarrior__project(self):
        """ By default, the project is the board name """
        expected_project = "Hyperspatial express route"
        self.assertEqual(expected_project,
                         self.issue.to_taskwarrior().get('project', None))


class TestTrelloService(ConfigTest):
    BOARD = {'id': 'B04RD', 'name': 'My Board'}
    CARD1 = {'id': 'C4RD', 'name': 'Card 1', 'members': [{'username': 'tintin'}],
             'due': '2018-12-02T12:59:00.000Z',
             'idShort': 1,
             'shortLink': 'abcd',
             'shortUrl': 'https://trello.com/c/AAaaBBbb',
             'labels': [{'name': 'foo'}, {'name': 'bar'}],
             'desc': 'some description',
             'url': 'https://trello.com/c/AAaBBbb/42-so-long'}
    CARD2 = {'id': 'kard', 'name': 'Card 2', 'members': [{'username': 'mario'}]}
    CARD3 = {'id': 'K4rD', 'name': 'Card 3', 'members': []}
    LIST1 = {'id': 'L15T', 'name': 'List 1'}
    LIST2 = {'id': 'ZZZZ', 'name': 'List 2'}
    COMMENT1 = {"type": "commentCard",
                "data": {"text": "Preums"},
                "memberCreator": {"username": "luidgi"}}
    COMMENT2 = {"type": "commentCard",
                "data": {"text": "Deuz"},
                "memberCreator": {"username": "mario"}}

    def setUp(self):
        super().setUp()
        self.config = {
            'general': {'targets': ['mytrello']},
            'mytrello': {
                'service': 'trello',
                'api_key': 'XXXX',
                'token': 'YYYY',
            },
        }
        responses.add(responses.GET,
                      'https://api.trello.com/1/lists/L15T/cards/open',
                      json=[self.CARD1, self.CARD2, self.CARD3])
        responses.add(responses.GET,
                      'https://api.trello.com/1/boards/B04RD/lists/open',
                      json=[self.LIST1, self.LIST2])
        responses.add(responses.GET,
                      'https://api.trello.com/1/boards/F00',
                      json={'id': 'F00', 'name': 'Foo Board'})
        responses.add(responses.GET,
                      'https://api.trello.com/1/boards/B4R',
                      json={'id': 'B4R', 'name': 'Bar Board'})
        responses.add(responses.GET,
                      'https://api.trello.com/1/members/me/boards',
                      json=[self.BOARD])
        responses.add(responses.GET,
                      'https://api.trello.com/1/cards/C4RD/actions',
                      json=[self.COMMENT1, self.COMMENT2])

    @responses.activate
    def test_get_boards_config(self):
        self.config['mytrello']['include_boards'] = 'F00, B4R'
        conf = self.validate()
        service = TrelloService(conf['mytrello'], conf['general'])
        boards = service.get_boards()
        self.assertEqual(list(boards), [{'id': 'F00', 'name': 'Foo Board'},
                                        {'id': 'B4R', 'name': 'Bar Board'}])

    @responses.activate
    def test_get_boards_api(self):
        conf = self.validate()
        service = TrelloService(conf['mytrello'], conf['general'])
        boards = service.get_boards()
        self.assertEqual(list(boards), [self.BOARD])

    @responses.activate
    def test_get_lists(self):
        conf = self.validate()
        service = TrelloService(conf['mytrello'], conf['general'])
        lists = service.get_lists('B04RD')
        self.assertEqual(list(lists), [self.LIST1, self.LIST2])

    @responses.activate
    def test_get_lists_include(self):
        self.config['mytrello']['include_lists'] = 'List 1'
        conf = self.validate()
        service = TrelloService(conf['mytrello'], conf['general'])
        lists = service.get_lists('B04RD')
        self.assertEqual(list(lists), [self.LIST1])

    @responses.activate
    def test_get_lists_exclude(self):
        self.config['mytrello']['exclude_lists'] = 'List 1'
        conf = self.validate()
        service = TrelloService(conf['mytrello'], conf['general'])
        lists = service.get_lists('B04RD')
        self.assertEqual(list(lists), [self.LIST2])

    @responses.activate
    def test_get_cards(self):
        conf = self.validate()
        service = TrelloService(conf['mytrello'], conf['general'])
        cards = service.get_cards('L15T')
        self.assertEqual(list(cards), [self.CARD1, self.CARD2, self.CARD3])

    @responses.activate
    def test_get_cards_assigned(self):
        self.config['mytrello']['only_if_assigned'] = 'tintin'
        conf = self.validate()
        service = TrelloService(conf['mytrello'], conf['general'])
        cards = service.get_cards('L15T')
        self.assertEqual(list(cards), [self.CARD1])

    @responses.activate
    def test_get_cards_assigned_unassigned(self):
        self.config['mytrello'].update({
            'only_if_assigned': 'tintin',
            'also_unassigned': 'true',
        })
        conf = self.validate()
        service = TrelloService(conf['mytrello'], conf['general'])
        cards = service.get_cards('L15T')
        self.assertEqual(list(cards), [self.CARD1, self.CARD3])

    @responses.activate
    def test_get_comments(self):
        conf = self.validate()
        service = TrelloService(conf['mytrello'], conf['general'])
        comments = service.get_comments('C4RD')
        self.assertEqual(list(comments), [self.COMMENT1, self.COMMENT2])

    @responses.activate
    def test_annotations(self):
        conf = self.validate()
        service = TrelloService(conf['mytrello'], conf['general'])
        annotations = service.annotations(self.CARD1)
        self.assertEqual(
            list(annotations), ["@luidgi - Preums", "@mario - Deuz"])

    @responses.activate
    def test_annotations_with_link(self):
        self.config['general']['annotation_links'] = 'true'
        conf = self.validate()
        service = TrelloService(conf['mytrello'], conf['general'])
        annotations = service.annotations(self.CARD1)
        self.assertEqual(
            list(annotations),
            ["https://trello.com/c/AAaaBBbb",
             "@luidgi - Preums",
             "@mario - Deuz"])

    @responses.activate
    def test_issues(self):
        self.config['mytrello'].update({
            'include_lists': 'List 1',
            'only_if_assigned': 'tintin',
        })
        conf = self.validate()
        service = TrelloService(conf['mytrello'], conf['general'])
        issues = service.issues()
        expected = {
            'due': parse_date('2018-12-02T12:59:00.000Z'),
            'description': '(bw)#1 - Card 1 .. https://trello.com/c/AAaaBBbb',
            'priority': 'M',
            'project': 'My Board',
            'trelloboard': 'My Board',
            'trellolist': 'List 1',
            'trellocard': 'Card 1',
            'trellocardid': 'C4RD',
            'trellocardidshort': 1,
            'trellodescription': 'some description',
            'trelloshortlink': 'abcd',
            'trelloshorturl': 'https://trello.com/c/AAaaBBbb',
            'trellourl': 'https://trello.com/c/AAaBBbb/42-so-long',
            'annotations': [
                "@luidgi - Preums",
                "@mario - Deuz"],
            'tags': []}
        actual = next(issues).get_taskwarrior_record()
        self.assertEqual(expected, actual)

    maxDiff = None

    def test_validate_config(self):
        self.validate()

    def test_valid_config_no_access_token(self):
        del self.config['mytrello']['token']

        self.assertValidationError(
            '[mytrello]\ntoken  <- field required')

    def test_valid_config_no_api_key(self):
        del self.config['mytrello']['api_key']

        self.assertValidationError(
            '[mytrello]\napi_key  <- field required')

    def test_keyring_service(self):
        """ Checks that the keyring service name """
        conf = self.validate()
        keyring_service = TrelloService.get_keyring_service(conf['mytrello'])
        self.assertEqual("trello://XXXX@trello.com", keyring_service)
