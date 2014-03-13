import httplib as http
import functools

from framework import request, redirect
from framework.exceptions import HTTPError
from framework.auth import get_current_user, get_api_key
from framework.auth.decorators import Auth

from website.models import Node


def _kwargs_to_nodes(kwargs):
    """Retrieve project and component objects from keyword arguments.

    :param dict kwargs: Dictionary of keyword arguments
    :return: Tuple of project and component

    """
    project = kwargs.get('project') or Node.load(kwargs['pid'])
    if not project:
        raise HTTPError(http.NOT_FOUND)
    if project.category != 'project':
        raise HTTPError(http.BAD_REQUEST)
    if project.is_deleted:
        raise HTTPError(http.GONE)

    if kwargs.get('nid') or kwargs.get('node'):
        node = kwargs.get('node') or Node.load(kwargs.get('nid'))
        if not node:
            raise HTTPError(http.NOT_FOUND)
        if node.is_deleted:
            raise HTTPError(http.GONE)
    else:
        node = None

    return project, node


def must_be_valid_project(func):

    # TODO: Check private link

    @functools.wraps(func)
    def wrapped(*args, **kwargs):

        kwargs['project'], kwargs['node'] = _kwargs_to_nodes(kwargs)
        return func(*args, **kwargs)

    return wrapped


def must_not_be_registration(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):

        kwargs['project'], kwargs['node'] = _kwargs_to_nodes(kwargs)
        node = kwargs['node'] or kwargs['project']

        if node.is_registration:
            raise HTTPError(http.BAD_REQUEST)
        return func(*args, **kwargs)

    return wrapped


def _must_be_contributor_factory(include_public):
    """Decorator factory for authorization wrappers. Decorators verify whether
    the current user is a contributor on the current project, or optionally
    whether the current project is public.

    :param bool include_public: Check whether current project is public
    :return: Authorization decorator

    """
    def wrapper(func):

        @functools.wraps(func)
        def wrapped(*args, **kwargs):

            kwargs['project'], kwargs['node'] = _kwargs_to_nodes(kwargs)
            node = kwargs['node'] or kwargs['project']

            kwargs['auth'] = Auth.from_kwargs(request.args.to_dict(), kwargs)
            user = kwargs['auth'].user

            if 'api_node' in kwargs:
                api_node = kwargs['api_node']
            else:
                api_node = get_api_key()
                kwargs['api_node'] = api_node

            if not node.is_public or not include_public:
                if user is None:
                    return redirect('/login/?next={0}'.format(request.path))
                if not node.is_contributor(user) \
                        and api_node != node:
                    raise HTTPError(http.FORBIDDEN)

            return func(*args, **kwargs)

        return wrapped

    return wrapper

# Create authorization decorators
must_be_contributor = _must_be_contributor_factory(False)
must_be_contributor_or_public = _must_be_contributor_factory(True)


def must_have_addon(addon_name, model):
    """Decorator factory that ensures that a given addon has been added to
    the target node. The decorated function will throw a 404 if the required
    addon is not found. Must be applied after a decorator that adds `node` and
    `project` to the target function's keyword arguments, such as
    `must_be_contributor.

    :param str addon_name: Name of addon
    :param str model: Name of model
    :return function: Decorator function

    """
    def wrapper(func):

        @functools.wraps(func)
        def wrapped(*args, **kwargs):

            if model == 'node':
                owner = kwargs['node'] or kwargs['project']
            elif model == 'user':
                owner = get_current_user()
                if owner is None:
                    raise HTTPError(http.UNAUTHORIZED)
            else:
                raise HTTPError(http.BAD_REQUEST)

            addon = owner.get_addon(addon_name)
            if addon is None:
                raise HTTPError(http.BAD_REQUEST)
            kwargs['{0}_addon'.format(model)] = addon

            return func(*args, **kwargs)

        return wrapped

    return wrapper


def must_have_permission(permission):
    """Decorator factory for checking permissions. Checks that user is logged
    in and has necessary permissions for node. Node must be passed in keyword
    arguments to view function.

    :param list permissions: List of accepted permissions
    :returns: Decorator function for checking permissions
    :raises: HTTPError(http.UNAUTHORIZED) if not logged in
    :raises: HTTPError(http.FORBIDDEN) if missing permissions

    """
    def wrapper(func):

        @functools.wraps(func)
        def wrapped(*args, **kwargs):

            # Ensure `project` and `node` kwargs
            kwargs['project'], kwargs['node'] = _kwargs_to_nodes(kwargs)
            node = kwargs['node'] or kwargs['project']

            kwargs['auth'] = Auth.from_kwargs(request.args.to_dict(), kwargs)
            user = kwargs['auth'].user

            # User must be logged in
            if user is None:
                raise HTTPError(http.UNAUTHORIZED)

            # User must have permissions
            if not node.has_permission(user, permission):
                raise HTTPError(http.FORBIDDEN)

            # Call view function
            return func(*args, **kwargs)

        # Return decorated function
        return wrapped

    # Return decorator
    return wrapper
