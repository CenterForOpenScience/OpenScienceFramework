from datetime import datetime, timedelta
from nose.tools import *  # noqa
from framework.mongo import database
from framework.transactions.context import TokuTransaction

from website.models import User
from tests.base import OsfTestCase
from tests.factories import AuthUserFactory
from scripts.analytics.user_summary import UserSummary


def modify_user_dates_in_mongo(new_date):
    with TokuTransaction():
        for user in database.user.find():
            database['user'].find_and_modify(
                {'_id': user['_id']},
                {'$set': {
                    'date_registered': new_date
                }}
            )

class TestUserCount(OsfTestCase):
    def setUp(self):
        self.yesterday = datetime.today() - timedelta(1)
        self.a_while_ago = datetime.today() - timedelta(2)
        super(TestUserCount, self).setUp()
        for i in range(0, 3):
            u = AuthUserFactory()
            u.is_registered = True
            u.password = 'wow' + str(i)
            u.date_confirmed = self.yesterday
            u.save()
        u = AuthUserFactory()
        u.is_registered = True
        u.password = 'wow'
        u.date_confirmed = self.a_while_ago
        u.save()
        for i in range(0, 2):
            u = AuthUserFactory()
            u.date_confirmed = None
            u.save()
        u = AuthUserFactory()
        u.date_disabled = self.yesterday
        u.save()
        u = AuthUserFactory()
        u.date_disabled = self.a_while_ago
        u.save()

        modify_user_dates_in_mongo(self.yesterday)

    def tearDown(self):
        User.remove()

    def test_gets_users(self):
        data = UserSummary().get_events(self.yesterday.date())[0]
        assert_equal(data['status']['active'], 4)
        assert_equal(data['status']['unconfirmed'], 2)
        assert_equal(data['status']['deactivated'], 2)

    def test_gets_only_users_from_given_date(self):
        data = UserSummary().get_events(self.a_while_ago.date())[0]
        assert_equal(data['status']['active'], 1)
        assert_equal(data['status']['unconfirmed'], 0)
        assert_equal(data['status']['deactivated'], 1)
