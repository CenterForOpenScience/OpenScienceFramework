from collections import OrderedDict
from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, LinksField, Link, LinksFieldNoSelfLink


class UserSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'fullname',
        'given_name',
        'middle_name',
        'family_name',
        'id'
    ])
    id = ser.CharField(read_only=True, source='_id')
    attributes = ser.SerializerMethodField(help_text='A dictionary containing user properties')
    links = LinksField({'html': 'absolute_url'})
    relationships = LinksFieldNoSelfLink({
        'nodes': {
            'links': {
                'related': Link('users:user-nodes', kwargs={'user_id': '<pk>'})
            }
        },
    })

    class Meta:
        type_ = 'users'

    @staticmethod
    def get_attributes(obj):
        ret = OrderedDict((
            ('fullname', obj.fullname),
            ('given_name', obj.given_name),
            ('middle_name', obj.middle_names),
            ('family_name', obj.family_name),
            ('suffix', obj.suffix),
            ('date_registered', obj.date_registered),
            ('gravatar_url', obj.gravatar_url),
            ('employment_institutions', obj.jobs),
            ('educational_institutions', obj.schools),
            ('social_accounts', obj.social)))
        if hasattr(obj, 'bibliographic'):
            ret['bibliographic'] = obj.bibliographic
        return ret

    def absolute_url(self, obj):
        return obj.absolute_url

    def update(self, instance, validated_data):
        # TODO
        pass


class ContributorSerializer(UserSerializer):

    local_filterable = frozenset(['bibliographic'])
    filterable_fields = frozenset.union(UserSerializer.filterable_fields, local_filterable)
