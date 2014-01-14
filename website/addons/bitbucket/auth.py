"""
Get access to Bitbucket using OAuth 1.0.
"""

import os
from requests_oauthlib import OAuth1Session

from website import settings
from . import settings as bitbucket_settings

OAUTH_REQUEST_TOKEN_URL = 'https://bitbucket.org/api/1.0/oauth/request_token'
OAUTH_AUTHORIZE_URL = 'https://bitbucket.org/api/1.0/oauth/authenticate'
OAUTH_ACCESS_TOKEN_URL = 'https://bitbucket.org/api/1.0/oauth/access_token'


def oauth_start_url(user, node=None):
    """Get authorization URL for OAuth.

    :param User user: OSF user
    :param Node node: OSF node
    :return tuple: Tuple of authorization URL and OAuth state

    """
    uri_parts = [
        settings.DOMAIN, 'api', 'v1', 'addons', 'bitbucket',
        'callback', user._id,
    ]
    if node:
        uri_parts.append(node._id)
    callback_uri = os.path.join(*uri_parts)

    session = OAuth1Session(
        bitbucket_settings.CLIENT_ID,
        client_secret=bitbucket_settings.CLIENT_SECRET,
        callback_uri=callback_uri,
    )

    request_key = session.fetch_request_token(OAUTH_REQUEST_TOKEN_URL)
    resource_owner_key = request_key.get('oauth_token')
    resource_owner_secret = request_key.get('oauth_token_secret')

    authorization_url = session.authorization_url(OAUTH_AUTHORIZE_URL)

    return resource_owner_key, resource_owner_secret, authorization_url


def oauth_get_token(owner_key, owner_secret, verifier):
    """Get OAuth access token.

    :param str code: Authorization code from provider
    :return str: OAuth access token

    """

    session = OAuth1Session(
        bitbucket_settings.CLIENT_ID,
        client_secret=bitbucket_settings.CLIENT_SECRET,
        resource_owner_key=owner_key,
        resource_owner_secret=owner_secret,
        verifier=verifier,
    )

    access_tokens = session.fetch_access_token(OAUTH_ACCESS_TOKEN_URL)
    access_token = access_tokens.get('oauth_token')
    access_token_secret = access_tokens.get('oauth_token_secret')

    return access_token, access_token_secret
