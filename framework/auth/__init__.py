# -*- coding: utf-8 -*-
import logging

from framework import session, create_session
from framework import goback
from framework import status, redirect, request
from framework.auth.utils import parse_name
from framework.exceptions import HTTPError
import framework.flask as web
import framework.bcrypt as bcrypt
from modularodm.query.querydialect import DefaultQueryDialect as Q
import helper
from model import User

from decorator import decorator
import datetime

import httplib as http


def get_current_username():
    return session.data.get('auth_user_username')


def get_current_user_id():
    return session.data.get('auth_user_id')


def get_current_user():
    uid = session._get_current_object() and session.data.get('auth_user_id')
    return User.load(uid)


def get_display_name(username):
    """Return the username to display in the navbar. Shortens long usernames."""
    if len(username) > 22:
        return '%s...%s' % (username[:9], username[-10:])
    return username


def get_current_node():
    from website.models import Node
    nid = session.data.get('auth_node_id')
    if nid:
        return Node.load(nid)


def get_api_key():
    # Hack: Avoid circular import
    from website.project.model import ApiKey
    api_key = session.data.get('auth_api_key')
    return ApiKey.load(api_key)


def get_user_or_node():
    uid = get_current_user()
    if uid:
        return uid
    return get_current_node()


# check_password(actual_pw_hash, given_password) -> Boolean
check_password = bcrypt.check_password_hash


def get_user(id=None, username=None, password=None, verification_key=None):
    # tag: database
    query_list = []
    if id:
        query_list.append(Q('_id', 'eq', id))
    if username:
        username = username.strip().lower()
        query_list.append(Q('username', 'eq', username))
    if password:
        password = password.strip()
        try:
            query = query_list[0]
            for query_part in query_list[1:]:
                query = query & query_part
            print 'query', query
            user = User.find_one(query)
            print 'user', user
        except Exception as err:
            logging.error(err)
            user = None
        if user and not user.check_password(password):
            logging.debug("Incorrect password attempt.")
            return False
        return user
    if verification_key:
        query_list.append(Q('verification_key', 'eq', verification_key))
    try:
        query = query_list[0]
        for query_part in query_list[1:]:
            query = query & query_part
        user = User.find_one(query)
        return user
    except Exception as err:
        logging.error(err)
        return None


def login(username, password):
    username = username.strip().lower()
    password = password.strip()
    logging.info("Attempting to log in {0}".format(username))

    if username and password:
        user = get_user(
            username=username,
            password=password
        )
        if user:
            if not user.is_registered:
                logging.debug("User is not registered")
                return 2
            elif not user.is_claimed:
                logging.debug("User is not claimed")
                return False
            else:
                is_first_login = user.date_last_login is None
                user.date_last_login = datetime.datetime.utcnow()
                user.save()
                if not is_first_login:
                    response = goback()
                else:
                    # Direct user to settings page if first login; need to
                    # verify imputed names
                    status.push_status_message('Welcome to the OSF! Please update the '
                                        'following settings. If you need assistance '
                                        'in getting started, please visit the '
                                        '<a href="/getting-started/">Getting Started</a> '
                                        'page.')
                    response = web.redirect('/settings/')
                data = session.data if session._get_current_object() else {}
                data.update({
                    'auth_user_username': user.username,
                    'auth_user_id': user._primary_key,
                    'auth_user_fullname': user.fullname,
                })
                response = create_session(response, data=data)
                return response
    return False

def logout():
    for key in ['auth_user_username', 'auth_user_id', 'auth_user_fullname']:
        # todo leave username so login page can persist probable id
        del session.data[key]
    return True

def add_unclaimed_user(email, fullname):
    email = email.strip().lower()
    fullname = fullname.strip()

    user = get_user(username=email)
    if user:
        return user
    else:
        user_based_on_email = User.find_one(
            Q('emails', 'eq', email)
        )
        if user_based_on_email:
            return user_based_on_email
        newUser = User(
            fullname = fullname,
            emails = [email],
        )
        newUser._optimistic_insert()
        newUser.save()
        return newUser


class DuplicateEmailError(BaseException):
    pass


def register(username, password, fullname):
    username = username.strip().lower()
    fullname = fullname.strip()

    # TODO: This validation should occur at the database level, not the view
    if not get_user(username=username):
        parsed = parse_name(fullname)
        newUser = User(
            username=username,
            fullname=fullname,
            is_registered=True,
            is_claimed=True,
            verification_key=helper.random_string(15),
            date_registered=datetime.datetime.utcnow(),
            **parsed
        )
        # Set the password
        newUser.set_password(password.strip())
        newUser.emails.append(username.strip())
        newUser.save()
        return newUser
    else:
        raise DuplicateEmailError

#### Auth-related decorators ##################################################


def must_be_logged_in(fn):
    '''Require that user be logged in. Modifies kwargs to include the current
    user.
    '''
    def wrapped(func, *args, **kwargs):
        user = get_current_user()
        if user:
            kwargs['user'] = user
            return func(*args, **kwargs)
        else:
            return redirect('/login/?next={0}'.format(request.path))
    return decorator(wrapped, fn)


def must_have_session_auth(fn):
    '''Require session authentication. Modifies kwargs to include the current
    user, api_key, and node if they exist.
    '''
    def wrapped(func, *args, **kwargs):

        kwargs['user'] = get_current_user()
        kwargs['api_key'] = get_api_key()
        kwargs['api_node'] = get_current_node()
        if kwargs['user'] or kwargs['api_key']:
            return func(*args, **kwargs)
        # kwargs['api_node'] = get_current_node()

        # Get user from session
        # user = get_current_user()
        # if kwargs['user']:
            # kwargs['user'] = user
            # return func(*args, **kwargs)

        # Get node from session
        # node = get_current_node()
        # if node:
        # if kwargs['api_key']:
            # kwargs['api_node'] = node
            # return func(*args, **kwargs)
        # No session authentication found
        return redirect('/login/?next={0}'.format(request.path))

    return decorator(wrapped, fn)
