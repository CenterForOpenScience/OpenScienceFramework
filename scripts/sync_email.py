"""
Subscribe all registered OSF users to the 'Open Science Framework General'
mailing list on mailchimp. From the API docs:

1. Grab the users to be updated or created
2. For each user's status, sort them into two batches:
    Users to be subscribed or updated
    Users to be unsubscribed
3. For each of those batches, use:
    listBatchSubscribe() to add new or update existing users on your List
    listBatchUnsubscribe() to remove old users from your List

http://apidocs.mailchimp.com/api/how-to/sync-you-to-mailchimp.php
"""

from modularodm import Q
from framework.auth.core import User
from framework.auth import utils
from website.app import init_app
from tests.base import OsfTestCase
from tests.factories import UserFactory, UnconfirmedUserFactory
from nose.tools import *
import mock


def main():
    # Set up storage backends
    init_app(routes=False)
    subscribe = subscribe_users(list_name='Open Science Framework General') #confirm list name before running script
    print '{n} users subscribed'.format(n=subscribe['add_count'])


def get_user_emails():
    # Format to subscribe users in bulk: [{'email': {'email: email'}},
    # Exclude unconfirmed and unregistered users
    return [
        {'email': {'email': user.username}, 'email_type': 'html'} for user
        in User.find(Q('is_registered', 'eq', True))
    ]


def subscribe_users(list_name):
    m = utils.get_mailchimp_api()
    list_id = utils.get_list_id_from_name(list_name=list_name)
    return m.lists.batch_subscribe(id=list_id, batch=get_user_emails(), double_optin=False)


class TestSyncEmail(OsfTestCase):

    def setUp(self):
        super(TestSyncEmail, self).setUp()
        self.user = UserFactory()
        self.unregistered = UnconfirmedUserFactory()

    def test_get_user_emails(self):
        emails = get_user_emails()
        expected = [{'email': {'email': self.user.username}, 'email_type': 'html'}]
        assert_equal(len(emails), 1)
        assert_equal(expected, emails)

    @mock.patch('framework.auth.utils.mailchimp.Lists.list')
    @mock.patch('framework.auth.utils.mailchimp.Lists.batch_subscribe')
    def test_subscribe_users_called_with_correct_arguments(self, mock_subscribe, mock_list):
        list_name = 'foo'
        mock_list.return_value = {'data': [{'id': 1, 'list_name': list_name}]}
        list_id = utils.get_list_id_from_name(list_name)
        batch = [{'email': {'email': self.user.username}, 'email_type': 'html'}]
        subscribe_users(list_name=list_name)
        mock_subscribe.assert_called_with(id=list_id, batch=batch, double_optin=False)


if __name__ == '__main__':
    main()