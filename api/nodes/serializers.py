from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, LinksField, Link
from website.models import Node
from framework.auth.core import Auth


class NodeSerializer(JSONAPISerializer):

    filterable_fields = ['title', 'description']

    id = ser.CharField(read_only=True, source='_id')
    title = ser.CharField(required=True)
    description = ser.CharField(required=False, allow_blank=True)
    category = ser.ChoiceField(choices=Node.CATEGORY_MAP.keys())
    date_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)
    tags = ser.SerializerMethodField()

    links = LinksField({
        'html': 'absolute_url',
        'children': {
            'related': Link('nodes:node-children', kwargs={'pk': '<pk>'})
        },
        'contributors': {
            'related': Link('nodes:node-contributors', kwargs={'pk': '<pk>'})
        },
        'pointers': {
            'related': Link('nodes:node-pointers', kwargs={'pk': '<pk>'})
        },
        'registrations': {
            'related': Link('nodes:node-registrations', kwargs={'pk': '<pk>'})
        },
    })
    properties = ser.SerializerMethodField()
    public = ser.BooleanField(source='is_public')
    # TODO: finish me

    class Meta:
        type_ = 'nodes'

    @staticmethod
    def get_properties(obj):
        ret = {
            'registration': obj.is_registration,
            'collection': obj.is_folder,
            'dashboard': obj.is_dashboard,
        }
        return ret

    @staticmethod
    def get_tags(obj):
        ret = {
            'system': [tag._id for tag in obj.system_tags],
            'user': [tag._id for tag in obj.tags],
        }
        return ret

    def create(self, validated_data):
        node = Node(**validated_data)
        node.save()
        return node

    def update(self, instance, validated_data):
        """Update instance with the validated data. Requires
        the request to be in the serializer context.
        """
        assert isinstance(instance, Node), 'instance must be a Node'
        is_public = validated_data.pop('is_public')
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        request = self.context['request']
        user = request.user
        auth = Auth(user)
        if is_public != instance.is_public:
            privacy = 'public' if is_public else 'private'
            instance.set_privacy(privacy, auth)
        instance.save()
        return instance


class NodePointersSerializer(JSONAPISerializer):

    id = ser.CharField(read_only=True, source='_id')
    node_id = ser.CharField(source='node._id')
    title = ser.CharField(source='node.title')

    class Meta:
        type_ = 'pointers'

    links = LinksField({
        'html': 'absolute_url',
    })

    def create(self, validated_data):
        # TODO
        pass

    def update(self, instance, validated_data):
        # TODO
        pass
