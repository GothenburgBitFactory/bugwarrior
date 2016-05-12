""" Tools for querying github.

I tried using pygithub3, but it really sucks.
"""

import requests

from bugwarrior.services import ServiceClient


def _link_field_to_dict(field):
    """ Utility for ripping apart github's Link header field.
    It's kind of ugly.
    """

    if not field:
        return dict()

    return dict([
        (
            part.split('; ')[1][5:-1],
            part.split('; ')[0][1:-1],
        ) for part in field.split(', ')
    ])


class GithubClient(ServiceClient):
    def __init__(self, auth):
        self.auth = auth

    def get_repos(self, username):
        tmpl = "https://api.github.com/users/{username}/repos?per_page=100"
        url = tmpl.format(username=username)
        return self._getter(url)

    def get_involved_issues(self, username):
        tmpl = "https://api.github.com/search/issues?q=involves%3A{username}&per_page=100"
        url = tmpl.format(username=username)
        return self._getter(url, subkey='items')

    def get_issues(self, username, repo):
        tmpl = "https://api.github.com/repos/{username}/{repo}/issues?per_page=100"
        url = tmpl.format(username=username, repo=repo)
        return self._getter(url)

    def get_directly_assigned_issues(self):
        """ Returns all issues assigned to authenticated user.

        This will return all issues assigned to the authenticated user
        regardless of whether the user owns the repositories in which the
        issues exist.
        """
        url = "https://api.github.com/user/issues?per_page=100"
        return self._getter(url)

    def get_comments(self, username, repo, number):
        tmpl = "https://api.github.com/repos/{username}/{repo}/issues/" + \
            "{number}/comments?per_page=100"
        url = tmpl.format(username=username, repo=repo, number=number)
        return self._getter(url)

    def get_pulls(self, username, repo):
        tmpl = "https://api.github.com/repos/{username}/{repo}/pulls?per_page=100"
        url = tmpl.format(username=username, repo=repo)
        return self._getter(url)

    def _getter(self, url, subkey=None):
        """ Pagination utility.  Obnoxious. """

        kwargs = {}

        if 'token' in self.auth:
            kwargs['headers'] = {
                'Authorization': 'token ' + self.auth['token']
            }
        elif 'basic' in self.auth:
            kwargs['auth'] = self.auth['basic']

        results = []
        link = dict(next=url)

        while 'next' in link:
            response = requests.get(link['next'], **kwargs)
            json_res = self.json_response(response)

            if subkey is not None:
                json_res = json_res[subkey]

            results += json_res

            link = _link_field_to_dict(response.headers.get('link', None))

        return results
