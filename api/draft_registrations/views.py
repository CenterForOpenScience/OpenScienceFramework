import requests

from rest_framework import status
from framework.auth.core import Auth
from rest_framework.response import Response
from django.utils.translation import ugettext_lazy as _
from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import PermissionDenied, ValidationError

from modularodm import Q
from website.models import DraftRegistration
from api.base.filters import ODMFilterMixin
from website.language import REGISTER_WARNING
from api.base.utils import waterbutler_url_for
from api.nodes.serializers import NodePointersSerializer
from api.base.utils import token_creator, absolute_reverse
from api.nodes.permissions import ContributorOrPublic, ReadOnlyIfRegistration
from api.nodes.views import NodeMixin, NodeFilesList, NodeChildrenList, NodeContributorsList, NodeDetail
from api.draft_registrations.serializers import DraftRegistrationSerializer, DraftRegistrationCreateSerializer, DraftRegistrationCreateSerializerWithToken


def registration_enforcer(node):
    if node.is_registration is False and node.is_registration_draft is False:
        raise ValidationError(_('Not a registration or registration draft.'))


class DraftRegistrationMixin(NodeMixin):
    """Mixin with convenience methods for retrieving the current node based on the
    current URL. By default, fetches the current node based on the pk kwarg.
    """

    serializer_class = DraftRegistrationSerializer
    node_lookup_url_kwarg = 'registration_id'


class DraftRegistrationList(generics.ListAPIView, ODMFilterMixin):
    """All draft registrations"""

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )
    serializer_class = DraftRegistrationSerializer

    # overrides ListAPIView
    def get_queryset(self):
        user = self.request.user
        return DraftRegistration.find(Q('initiator', 'eq', user))


class DraftRegistrationDetail(NodeDetail, generics.CreateAPIView, DraftRegistrationMixin):
    """
    Registration details
    """
    permission_classes = (
        ContributorOrPublic,
        ReadOnlyIfRegistration,
    )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            serializer_class = DraftRegistrationCreateSerializer
            return serializer_class
        serializer_class = DraftRegistrationSerializer
        return serializer_class

    # Restores original get_serializer_class
    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }

    # overrides RetrieveAPIView
    def get_object(self):
        node = self.get_node()
        registration_enforcer(node)
        return self.get_node()

    # overrides CreateAPIView
    def create(self, request, registration_id):
        user = request.user
        node = self.get_node()
        if node.is_registration_draft is False:
            raise ValidationError(_('Not a registration draft.'))
        token = token_creator(node._id, user._id)
        url = absolute_reverse('registrations:registration-create', kwargs={'registration_id': node._id, 'token': token})
        registration_warning = REGISTER_WARNING.format((node.title))
        return Response({'data': {'id': node._id, 'warning_message': registration_warning, 'links': {'confirm_delete': url}}}, status=status.HTTP_202_ACCEPTED)


class DraftRegistrationCreate(generics.CreateAPIView, DraftRegistrationMixin):
    """
    Save your registration draft
    """
    permission_classes = (
        ContributorOrPublic,
        ReadOnlyIfRegistration,
    )

    serializer_class = DraftRegistrationCreateSerializerWithToken


class DraftRegistrationContributorsList(NodeContributorsList, DraftRegistrationMixin):
    """
    Contributors(users) for a registration
    """
    def get_default_queryset(self):
        node = self.get_node()
        registration_enforcer(node)
        visible_contributors = node.visible_contributor_ids
        contributors = []
        for contributor in node.contributors:
            contributor.bibliographic = contributor._id in visible_contributors
            contributors.append(contributor)
        return contributors


class DraftRegistrationChildrenList(NodeChildrenList, DraftRegistrationMixin):
    """
    Children of the current registration
    """
    def get_queryset(self):
        reg_node = self.get_node()
        registration_enforcer(reg_node)
        nodes = reg_node.nodes
        user = self.request.user
        if user.is_anonymous():
            auth = Auth(None)
        else:
            auth = Auth(user)
        children = [node for node in nodes if node.can_view(auth) and node.primary]
        return children


class DraftRegistrationPointersList(generics.ListAPIView, DraftRegistrationMixin):
    """
    Registration pointers
    """

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
    )

    serializer_class = NodePointersSerializer

    def get_queryset(self):
        node = self.get_node()
        registration_enforcer(node)
        pointers = node.nodes_pointer
        return pointers


class DraftRegistrationFilesList(NodeFilesList, DraftRegistrationMixin):
    """
    Files attached to a registration
    """
    def get_queryset(self):
        query_params = self.request.query_params
        node = self.get_node()
        registration_enforcer(node)
        addons = node.get_addons()
        user = self.request.user
        cookie = None if self.request.user.is_anonymous() else user.get_or_create_cookie()
        node_id = node._id
        obj_args = self.request.parser_context['args']

        provider = query_params.get('provider')
        path = query_params.get('path', '/')
        files = []

        if provider is None:
            valid_self_link_methods = self.get_valid_self_link_methods(True)
            for addon in addons:
                if addon.config.has_hgrid_files:
                    files.append({
                        'valid_self_link_methods': valid_self_link_methods['folder'],
                        'provider': addon.config.short_name,
                        'name': addon.config.short_name,
                        'path': path,
                        'node_id': node_id,
                        'cookie': cookie,
                        'args': obj_args,
                        'waterbutler_type': 'file',
                        'item_type': 'folder',
                        'metadata': {},
                    })
        else:
            url = waterbutler_url_for('data', provider, path, self.kwargs['node_id'], cookie, obj_args)
            waterbutler_request = requests.get(url)
            if waterbutler_request.status_code == 401:
                raise PermissionDenied
            try:
                waterbutler_data = waterbutler_request.json()['data']
            except KeyError:
                raise ValidationError(detail='detail: Could not retrieve files information.')

            if isinstance(waterbutler_data, list):
                for item in waterbutler_data:
                    file = self.get_file_item(item, cookie, obj_args)
                    files.append(file)
            else:
                files.append(self.get_file_item(waterbutler_data, cookie, obj_args))

        return files
