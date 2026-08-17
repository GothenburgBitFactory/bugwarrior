from dateutil.parser import parse as parse_date
import pytest
import responses

from bugwarrior.config.schema import MainSectionConfig
from bugwarrior.services.trello import TrelloConfig, TrelloIssue

from ..base import get_validated_service, validate

SERVICE_CONFIG = {'service': 'trello', 'api_key': 'XXXX', 'token': 'YYYY'}


@pytest.fixture
def record():
    return {
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


class TestTrelloIssue:
    @pytest.fixture
    def issue(self, record):
        config = TrelloConfig(
            service='trello',
            api_key='abc123',
            token='def456',
            import_labels_as_tags=True,
            default_priority='M',
            label_template='trello_{{label}}',
            target="mytrello",
        )
        main_config = MainSectionConfig(
            targets=[], inline_links=True, description_length=31
        )
        extra = {'boardname': 'Hyperspatial express route', 'listname': 'Something'}
        return TrelloIssue(record, config, main_config, extra)

    def test_default_description(self, issue):
        """Test the generated description"""
        expected_desc = (
            "(bw)#42 - So long, and thanks for all the .. https://trello.com/c/AAaaBBbb"
        )
        assert expected_desc == issue.get_default_description()

    def test_to_taskwarrior__project(self, issue):
        """By default, the project is the board name"""
        expected_project = "Hyperspatial express route"
        assert expected_project == issue.to_taskwarrior().to_taskwarrior_data().get(
            'project', None
        )


@pytest.fixture
def board():
    return {'id': 'B04RD', 'name': 'My Board'}


@pytest.fixture
def cards():
    return [
        {
            'id': 'C4RD',
            'name': 'Card 1',
            'members': [{'username': 'tintin'}],
            'due': '2018-12-02T12:59:00.000Z',
            'idShort': 1,
            'shortLink': 'abcd',
            'shortUrl': 'https://trello.com/c/AAaaBBbb',
            'labels': [{'name': 'foo'}, {'name': 'bar'}],
            'desc': 'some description',
            'url': 'https://trello.com/c/AAaBBbb/42-so-long',
        },
        {'id': 'kard', 'name': 'Card 2', 'members': [{'username': 'mario'}]},
        {'id': 'K4rD', 'name': 'Card 3', 'members': []},
    ]


@pytest.fixture
def lists():
    return [{'id': 'L15T', 'name': 'List 1'}, {'id': 'ZZZZ', 'name': 'List 2'}]


@pytest.fixture
def comments():
    return [
        {
            "type": "commentCard",
            "data": {"text": "Preums"},
            "memberCreator": {"username": "luidgi"},
        },
        {
            "type": "commentCard",
            "data": {"text": "Deuz"},
            "memberCreator": {"username": "mario"},
        },
    ]


class TestTrelloService:
    @pytest.fixture
    def config(self):
        return {'general': {'targets': ['myservice']}, 'myservice': {**SERVICE_CONFIG}}

    @pytest.fixture(autouse=True)
    def mock_api(self, board, cards, lists, comments):
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            rsps.add(
                responses.GET,
                'https://api.trello.com/1/lists/L15T/cards/open',
                json=cards,
            )
            rsps.add(
                responses.GET,
                'https://api.trello.com/1/boards/B04RD/lists/open',
                json=lists,
            )
            rsps.add(
                responses.GET,
                'https://api.trello.com/1/boards/F00',
                json={'id': 'F00', 'name': 'Foo Board'},
            )
            rsps.add(
                responses.GET,
                'https://api.trello.com/1/boards/B4R',
                json={'id': 'B4R', 'name': 'Bar Board'},
            )
            rsps.add(
                responses.GET,
                'https://api.trello.com/1/members/me/boards',
                json=[board],
            )
            rsps.add(
                responses.GET,
                'https://api.trello.com/1/cards/C4RD/actions',
                json=comments,
            )
            yield rsps

    def test_get_boards_config(self, config):
        config['myservice']['include_boards'] = 'F00, B4R'
        service = get_validated_service(config)
        boards = service.get_boards()
        assert list(boards) == [
            {'id': 'F00', 'name': 'Foo Board'},
            {'id': 'B4R', 'name': 'Bar Board'},
        ]

    def test_get_boards_api(self, config, board):
        service = get_validated_service(config)
        boards = service.get_boards()
        assert list(boards) == [board]

    def test_get_lists(self, config, lists):
        service = get_validated_service(config)
        assert list(service.get_lists('B04RD')) == lists

    def test_get_lists_include(self, config, lists):
        config['myservice']['include_lists'] = 'List 1'
        service = get_validated_service(config)
        assert list(service.get_lists('B04RD')) == [lists[0]]

    def test_get_lists_exclude(self, config, lists):
        config['myservice']['exclude_lists'] = 'List 1'
        service = get_validated_service(config)
        assert list(service.get_lists('B04RD')) == [lists[1]]

    def test_get_cards(self, config, cards):
        service = get_validated_service(config)
        assert list(service.get_cards('L15T')) == cards

    def test_get_cards_assigned(self, config, cards):
        config['myservice']['only_if_assigned'] = 'tintin'
        service = get_validated_service(config)
        assert list(service.get_cards('L15T')) == [cards[0]]

    def test_get_cards_assigned_unassigned(self, config, cards):
        config['myservice'].update(
            {'only_if_assigned': 'tintin', 'also_unassigned': 'true'}
        )
        service = get_validated_service(config)
        assert list(service.get_cards('L15T')) == [cards[0], cards[2]]

    def test_get_comments(self, config, comments):
        service = get_validated_service(config)
        assert list(service.get_comments('C4RD')) == comments

    def test_annotations(self, config, cards):
        service = get_validated_service(config)
        annotations = service.annotations(cards[0])
        assert list(annotations) == ["@luidgi - Preums", "@mario - Deuz"]

    def test_annotations_with_link(self, config, cards):
        config['general']['annotation_links'] = 'true'
        service = get_validated_service(config)
        annotations = service.annotations(cards[0])
        assert list(annotations) == [
            "https://trello.com/c/AAaaBBbb",
            "@luidgi - Preums",
            "@mario - Deuz",
        ]

    def test_issues(self, config):
        config['myservice'].update(
            {'include_lists': 'List 1', 'only_if_assigned': 'tintin'}
        )
        service = get_validated_service(config)
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
            'annotations': ["@luidgi - Preums", "@mario - Deuz"],
            'tags': [],
        }
        actual = next(issues).to_taskwarrior_data()
        assert expected == actual

    def test_validate_config(self, config):
        validate(config)

    def test_valid_config_no_access_token(self, config, assert_validation_error):
        del config['myservice']['token']

        assert_validation_error(config, '[myservice]\ntoken  <- Field required')

    def test_valid_config_no_api_key(self, config, assert_validation_error):
        del config['myservice']['api_key']

        assert_validation_error(config, '[myservice]\napi_key  <- Field required')

    def test_keyring_service(self, config):
        """Checks that the keyring service name"""
        conf = validate(config)
        keyring_service = conf.service_configs[0].keyring_service
        assert "trello://XXXX@trello.com" == keyring_service
