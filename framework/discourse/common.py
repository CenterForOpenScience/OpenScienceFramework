import requests

from framework.discourse import settings

# Prevent unnecessary syncing to discourse from spurious differences during a migration
in_migration = False

class DiscourseException(Exception):
    """
    Raised when Discourse does not respond as expected to an HTTP request.

    :param str message: description of the error that occured
    :param requests.Response result: the Response object that indicated the error
    """
    def __init__(self, message, result=None):
        super(DiscourseException, self).__init__(message)
        self.result = result

def request(method, path, data=None, username=None):
    """Make an HTTP request to the Discourse server with api credentials.
    Return json dict object of the results, or None.
    Allows redirects only for the GET method.

    :param str method: the HTTP method to use (get, put, post, delete)
    :param str path: the endpoint to send the request to
    :param dict data: form or param data to send with the request
    :param str username: guid of the user to make the request as (default to settings.DISCOURSE_API_ADMIN_USER)
    :return dict: the json result from the query, if any
    """
    if not data:
        data = {}

    params = {
        'api_key': settings.DISCOURSE_API_KEY,
        'api_username': username if username else settings.DISCOURSE_API_ADMIN_USER
    }

    url = requests.compat.urljoin(settings.DISCOURSE_SERVER_URL, path)

    requestMethod = getattr(requests, method)
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    timeout = None if settings.DISCOURSE_DEV_MODE else 10
    result = requestMethod(url, data=data, params=params, allow_redirects=False, headers=headers, timeout=timeout)

    if settings.DISCOURSE_LOG_REQUESTS:
        print(method + ' \t' + result.request.url + ' with data: ' + str(data)[:200] + ' and params: ' + str(params)[:200])

    if result.is_redirect and method.lower() == 'get':
        # follow one redirect
        result = requests.get(result.headers['location'], data=data, params=params, allow_redirects=False, headers=headers, timeout=timeout)
        if settings.DISCOURSE_LOG_REQUESTS:
            print(method + ' \t' + result.request.url + ' with data: ' + str(data)[:200] + ' and params: ' + str(params)[:200])

    if result.status_code < 200 or result.status_code > 299:
        raise DiscourseException('Discourse server responded to ' + method + ' request ' + result.url + ' with '
                                 + ' post data ' + str(data) + ' with result code '
                                 + str(result.status_code) + ': ' + result.text[:500],
                                 result)

    try:
        return result.json()
    except ValueError:
        return None
