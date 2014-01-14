"""

"""

import os
import json
import base64
import urllib
import datetime

import requests
from requests_oauthlib import OAuth2Session
from hurry.filesize import size, alternative

from . import settings as github_settings

GH_URL = 'https://github.com/'
API_URL = 'https://api.github.com/'

# TODO: Move to redis / memcached
github_cache = {}


class GitHub(object):

    def __init__(self, access_token=None, token_type=None):

        if access_token and token_type:
            self.session = OAuth2Session(
                github_settings.CLIENT_ID,
                token={
                    'access_token': access_token,
                    'token_type': token_type,
                }
            )
        else:
            self.session = requests

    @classmethod
    def from_settings(cls, settings):
        if settings:
            return cls(
                access_token=settings.oauth_access_token,
                token_type=settings.oauth_token_type,
            )
        return cls()

    def _send(self, url, method='get', output='json', cache=True, **kwargs):
        """

        """
        func = getattr(self.session, method.lower())

        # Add if-modified-since header if needed
        headers = kwargs.pop('headers', {})
        cache_key = '{0}::{1}::{2}'.format(
            url, method, str(kwargs)
        )
        cache_data = github_cache.get(cache_key)
        if cache and cache_data:
            if 'if-modified-since' not in headers:
                headers['if-modified-since'] = cache_data['date'].strftime('%c')

        # Send request
        req = func(url, headers=headers, **kwargs)

        # Pull from cache if not modified
        if cache and cache_data and req.status_code == 304:
            return cache_data['data']

        # Get return value
        rv = None
        if 200 <= req.status_code < 300:
            if output is None:
                rv = req
            else:
                rv = getattr(req, output)
                if callable(rv):
                    rv = rv()

        # Cache return value if needed
        if cache and rv:
            if req.headers.get('last-modified'):
                github_cache[cache_key] = {
                    'data': rv,
                    'date': datetime.datetime.utcnow(),
                }

        return rv

    def repo(self, user, repo):

        return self._send(
            os.path.join(API_URL, 'repos', user, repo)
        )

    def branches(self, user, repo, branch=None):

        url = os.path.join(API_URL, 'repos', user, repo, 'branches')
        if branch:
            url = os.path.join(url, branch)

        return self._send(url)

    def commits(self, user, repo, path=None, sha=None):
        """Get commits for a repo or file.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :param str path: Path to file within repo
        :param str sha: SHA or branch name
        :return list: List of commit dicts from GitHub; see
            http://developer.github.com/v3/repos/commits/

        """
        return self._send(
            os.path.join(
                API_URL, 'repos', user, repo, 'commits'
            ),
            params={
                'path': path,
                'sha': sha,
            }
        )

    def history(self, user, repo, path, sha=None):
        """Get commit history for a file.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :param str path: Path to file within repo
        :param str sha: SHA or branch name
        :return list: List of dicts summarizing commits

        """
        req = self.commits(user, repo, path=path, sha=sha)

        if req:
            return [
                {
                    'sha': commit['sha'],
                    'name': commit['commit']['author']['name'],
                    'email': commit['commit']['author']['email'],
                    'date': commit['commit']['author']['date'],
                }
                for commit in req
            ]

    def tree(self, user, repo, sha, recursive=True, registration_data=None):
        """Get file tree for a repo.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :param str sha: Branch name or SHA
        :param bool recursive: Walk repo recursively
        :param dict registration_data: Registered commit data
        :return tuple: Tuple of commit ID and tree JSON; see
            http://developer.github.com/v3/git/trees/

        """
        req = self._send(os.path.join(
                API_URL, 'repos', user, repo, 'git', 'trees',
                urllib.quote_plus(sha),
            ),
            params={
                'recursive': int(recursive)
            },
        )

        if req is not None:
            return req
        return None

    def file(self, user, repo, path, ref=None):

        params = {
            'ref': ref,
        }

        req = self._send(
            os.path.join(
                API_URL, 'repos', user, repo, 'contents', path
            ),
            cache=True,
            params=params,
        )

        if req:
            content = req['content']
            return req['name'], base64.b64decode(content), req['size']

        return None, None, None

    def starball(self, user, repo, archive='tar', ref=None):
        """Get link for archive download.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :param str archive: Archive format [tar|zip]
        :param str ref: Git reference
        :return tuple: Tuple of headers and file location

        """
        url_parts = [
            API_URL, 'repos', user, repo, archive + 'ball'
        ]
        if ref:
            url_parts.append(ref)

        req = self._send(
            os.path.join(*url_parts),
            cache=False,
            output=None,
        )

        if req.status_code == 200:
            return dict(req.headers), req.content
        return None, None

    def set_privacy(self, user, repo, private):
        """Set privacy of GitHub repo.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :param bool private: Make repo private; see
            http://developer.github.com/v3/repos/#edit

        """
        req = self._send(
            os.path.join(
                API_URL, 'repos', user, repo
            ),
            method='patch',
            cache=False,
            data=json.dumps({
                'name': repo,
                'private': private,
            })
        )

        return req

    #########
    # Hooks #
    #########

    def hooks(self, user, repo):

        return self._send(
            os.path.join(
                API_URL, 'repos', user, repo, 'hooks',
            )
        )

    def add_hook(self, user, repo, name, config, events=None, active=True):

        data = {
            'name': name,
            'config': config,
            'events': events or ['push'],
            'active': active,
        }

        return self._send(
            os.path.join(
                API_URL, 'repos', user, repo, 'hooks'
            ),
            method='post',
            cache=False,
            data=json.dumps(data),
        )

    def delete_hook(self, user, repo, _id):

        return self._send(
            os.path.join(
                API_URL, 'repos', user, repo, 'hooks', str(_id),
            ),
            'delete',
            cache=False,
        )

    ########
    # CRUD #
    ########

    def upload_file(self, user, repo, path, message, content, sha=None, branch=None, committer=None, author=None):

        data = {
            'message': message,
            'content': base64.b64encode(content),
            'sha': sha,
            'branch': branch,
            'committer': committer,
            'author': author,
        }

        return self._send(
            os.path.join(
                API_URL, 'repos', user, repo, 'contents', path
            ),
            method='put',
            cache=False,
            data=json.dumps(data),
        )

    def delete_file(self, user, repo, path, message, sha, branch=None, committer=None, author=None):

        data = {
            'message': message,
            'sha': sha,
            'branch': branch,
            'committer': committer,
            'author': author,
        }

        return self._send(
            os.path.join(
                API_URL, 'repos', user, repo, 'contents', path
            ),
            method='delete',
            cache=False,
            data=json.dumps(data),
        )


def raw_url(user, repo, ref, path):
    return os.path.join(
        GH_URL, user, repo, 'blob', ref, path
    ) + '?raw=true'


type_map = {
    'tree': 'folder',
    'blob': 'file',
}


def tree_to_hgrid(tree, user, repo, node, branch=None, sha=None, hotlink=True):
    """Convert GitHub tree data to HGrid format.

    :param list tree: JSON description of git tree
    :param str user: GitHub user name
    :param str repo: GitHub repo name
    :param Node node: OSF Node
    :param str branch: Git branch
    :param str sha: Git SHA
    :param bool hotlink: Hotlink files if ref provided; will yield broken
        links if repo is private
    :return list: List of HGrid-formatted dicts

    """
    grid = []

    ref = urllib.urlencode({
        key: value
        for key, value in {
            'branch': branch,
            'sha': sha,
        }.iteritems()
        if value
    })

    parent = {
        'uid': 'tree:__repo__',
        'name': 'GitHub :: {0}'.format(repo),
        'parent_uid': 'null',
        'url': '',
        'type': 'folder',
        'uploadUrl': node.api_url + 'github/file/'
    }
    if ref:
        parent['uploadUrl'] += '?' + ref

    grid.append(parent)

    for item in tree:

        # Types should be "blob" or "tree" but may also be "commit". Ignore
        # unexpected types.
        if item['type'] not in type_map:
            continue

        split = os.path.split(item['path'])
        _, ext = os.path.splitext(item['path'])
        ext = ext.lstrip('.')

        row = {
            'uid': item['type'] + ':' + '||'.join(['__repo__', item['path']]),
            'name': split[1],
            'parent_uid': 'tree:' + '||'.join(['__repo__', split[0]]).strip('||'),
            'type': type_map[item['type']],
            'uploadUrl': node.api_url + 'github/file/',
        }
        if ref is not None:
             row['uploadUrl'] += '?ref=' + ref

        if item['type'] == 'blob':
            row['sha'] = item['sha']
            row['url'] = item['url']
            row['size'] = [
                item['size'],
                size(item['size'], system=alternative)
            ]
            row['ext'] = ext
            base_api_url = node.api_url + 'github/file/{0}/'.format(item['path'])
            row['delete'] = base_api_url + '?' + ref
            row['view'] = os.path.join(node.url, 'github', 'file', item['path']) + '/'
            if ref is not None:
                base_api_url += '?' + ref
                row['view'] += '?' + ref
            if hotlink and ref:
                row['download'] = raw_url(user, repo, sha or branch, item['path'])
            else:
                row['download'] = base_api_url
        else:
            row['uploadUrl'] = node.api_url + 'github/file/{0}/'.format(item['path'])
            if ref is not None:
                 row['uploadUrl'] += '?' + ref

        grid.append(row)

    return grid
