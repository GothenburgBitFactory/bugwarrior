""" Tools for querying github.

I tried using pygithub3, but it really sucks.
"""

import requests


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


def get_repos(username, auth):
    """ username should be a string
    auth should be a tuple of username and password.

    item can be one of "repos" or "orgs"
    """

    tmpl = "https://api.github.com/users/{username}/repos?per_page=100"
    url = tmpl.format(username=username)
    return _getter(url, auth)


def get_issues(username, repo, auth):
    """ username and repo should be strings
    auth should be a tuple of username and password.
    """

    tmpl = "https://api.github.com/repos/{username}/{repo}/issues?per_page=100"
    url = tmpl.format(username=username, repo=repo)
    return _getter(url, auth)


def get_directly_assigned_issues(auth):
    """ Returns all issues assigned to authenticated user.

    This will return all issues assigned to the authenticated user
    regardless of whether the user owns the repositories in which the
    issues exist.

    """
    url = "https://api.github.com/user/issues?per_page=100"
    return _getter(url, auth)


def get_comments(username, repo, number, auth):
    tmpl = "https://api.github.com/repos/{username}/{repo}/issues/" + \
        "{number}/comments?per_page=100"
    url = tmpl.format(username=username, repo=repo, number=number)
    return _getter(url, auth)


def get_pulls(username, repo, auth):
    """ username and repo should be strings
    auth should be a tuple of username and password.
    """

    tmpl = "https://api.github.com/repos/{username}/{repo}/pulls?per_page=100"
    url = tmpl.format(username=username, repo=repo)
    return _getter(url, auth)


def _getter(url, auth):
    """ Pagination utility.  Obnoxious. """

    kwargs = {}

    if 'token' in auth:
        kwargs['headers'] = {
            'Authorization': 'token ' + auth['token']
        }
    elif 'basic' in auth:
        kwargs['auth'] = auth['basic']

    results = []
    link = dict(next=url)
    while 'next' in link:
        response = requests.get(link['next'], **kwargs)

        # And.. if we didn't get good results, just bail.
        if response.status_code != 200:
            raise IOError(
                "Non-200 status code %r; %r; %r" % (
                    response.status_code, url, response.json))

        if callable(response.json):
            # Newer python-requests
            results += response.json()
        else:
            # Older python-requests
            results += response.json

        link = _link_field_to_dict(response.headers.get('link', None))

    return results

if __name__ == '__main__':
    # Little test.
    import getpass
    username = raw_input("GitHub Username: ")
    password = getpass.getpass()

    results = get_all(username, (username, password))
    print len(results), "repos found."
