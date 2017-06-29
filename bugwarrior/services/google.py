import httplib2
import os
import multiprocessing
import re

import googleapiclient.discovery
import oauth2client.client
import oauth2client.tools
import oauth2client.file

from bugwarrior.services import IssueService

import logging
log = logging.getLogger(__name__)

class GoogleService(IssueService):
    """Common abstract base class for google services."""
    DEFAULT_CLIENT_SECRET_PATH = '~/.gmail_client_secret.json'
    AUTHENTICATION_LOCK = multiprocessing.Lock()

    def __init__(self, *args, **kw):
        super(GoogleService, self).__init__(*args, **kw)

        self.login_name = self.config.get('login_name', 'me')
        self.client_secret_path = self.get_config_path(
                'client_secret_path',
                self.DEFAULT_CLIENT_SECRET_PATH)
        credentials_name = clean_filename(self.login_name
                if self.login_name != 'me' else self.target)
        self.credentials_path = os.path.join(
                self.config.data.path,
                '%s_credentials_%s.json' % (self.CONFIG_PREFIX, credentials_name,))
        self.api = self.build_api(self.RESOURCE)

    def get_config_path(self, varname, default_path=None):
        return os.path.expanduser(self.config.get(varname, default_path))

    def get_credentials(self):
        """Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.

        Returns:
            Credentials, the obtained credential.
        """
        with self.AUTHENTICATION_LOCK:
            log.info('Starting authentication for %s', self.target)
            store = oauth2client.file.Storage(self.credentials_path)
            credentials = store.get()
            if not credentials or credentials.invalid:
                log.info("No valid login. Starting OAUTH flow.")
                flow = oauth2client.client.flow_from_clientsecrets(self.client_secret_path, self.SCOPES)
                flow.user_agent = self.APPLICATION_NAME
                flags = oauth2client.tools.argparser.parse_args([])
                credentials = oauth2client.tools.run_flow(flow, store, flags)
                log.info('Storing credentials to %r', self.credentials_path)
            return credentials

    def build_api(self, resource):
        credentials = self.get_credentials()
        http = credentials.authorize(httplib2.Http())
        return googleapiclient.discovery.build(resource, 'v1', http=http)

def clean_filename(name):
    return re.sub(r'[^A-Za-z0-9_]+', '_', name)
