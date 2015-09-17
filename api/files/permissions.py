from rest_framework import permissions

from api.base.utils import get_user_auth
from website.files.models import FileNode


class ContributorOrPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, FileNode), 'obj must be a FileNode, got {}'.format(obj)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.node.is_public or obj.node.can_view(auth)
        if not obj.node.can_edit(auth):
            return False
        return True


class CheckedOutOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, FileNode), 'obj must be a FileNode, got {}'.format(obj)
        auth = get_user_auth(request)
        # Limited to osfstorage for the moment
        if obj.provider != 'osfstorage':
            return False
        return obj.checkout is None \
            or obj.checkout == auth.user \
            or obj.node.has_permission(auth.user, 'admin')


class ReadOnlyIfRegistration(permissions.BasePermission):
    """Makes PUT and POST forbidden for registrations."""

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, FileNode), 'obj must be a FileNode, got {}'.format(obj)
        if obj.node.is_registration:
            return request.method in permissions.SAFE_METHODS
        return True
