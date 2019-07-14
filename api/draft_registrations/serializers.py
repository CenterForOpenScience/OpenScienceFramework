from rest_framework import serializers as ser
from rest_framework import exceptions

from framework.exceptions import PermissionsError
from api.base.exceptions import InvalidModelValueError
from api.base.serializers import ValuesListField, RelationshipField, LinksField, HideIfDraft, IDField
from api.base.utils import absolute_reverse, get_user_auth
from api.nodes.serializers import (
    DraftRegistrationSerializerLegacy,
    DraftRegistrationDetailLegacySerializer,
    update_institutions,
    get_license_details,
    NodeLicenseSerializer,
    NodeLicenseRelationshipField,
    NodeContributorsSerializer,
    NodeContributorsCreateSerializer,
    NodeContributorDetailSerializer,
)
from api.taxonomies.serializers import TaxonomizableSerializerMixin
from osf.exceptions import DraftRegistrationStateError
from website import settings


class DraftRegistrationSerializer(DraftRegistrationSerializerLegacy, TaxonomizableSerializerMixin):
    title = ser.CharField(required=False)
    category_choices = settings.NODE_CATEGORY_MAP.items()
    category_choices_string = ', '.join(["'{}'".format(choice[0]) for choice in category_choices])

    description = ser.CharField(required=False, allow_blank=True, allow_null=True)
    category = ser.ChoiceField(required=False, choices=category_choices, help_text='Choices: ' + category_choices_string)
    tags = ValuesListField(attr_name='name', child=ser.CharField(), required=False)
    node_license = NodeLicenseSerializer(required=False, source='license')

    links = LinksField({
        'self': 'get_self_url',
    })

    license = NodeLicenseRelationshipField(
        related_view='licenses:license-detail',
        related_view_kwargs={'license_id': '<license.node_license._id>'},
        read_only=False,
    )

    contributors = RelationshipField(
        related_view='draft_registrations:draft-registration-contributors',
        related_view_kwargs={'draft_id': '<_id>'},
    )

    affiliated_institutions = RelationshipField(
        related_view='draft_registrations:draft-registration-institutions',
        related_view_kwargs={'draft_id': '<_id>'},
        self_view='draft_registrations:draft-registration-relationships-institutions',
        self_view_kwargs={'draft_id': '<_id>'},
        read_only=False,
        many=True,
        required=False,
    )

    @property
    def subjects_related_view(self):
        # Overrides TaxonomizableSerializerMixin
        return 'draft_registrations:draft-registration-subjects'

    @property
    def subjects_view_kwargs(self):
        # Overrides TaxonomizableSerializerMixin
        return {'draft_id': '<_id>'}

    @property
    def subjects_self_view(self):
        # Overrides TaxonomizableSerializerMixin
        return 'draft_registrations:draft-registration-relationships-subjects'

    def get_self_url(self, obj):
        return absolute_reverse(
            'draft_registrations:draft-registration-list',
            kwargs={
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    # Overrides DraftRegistrationSerializerLegacy
    def get_node(self, validated_data):
        return validated_data.pop('branched_from', None)

    def expect_subjects_as_relationships(self, request):
        """Determines whether subjects should be serialized as a relationship.
        Older serializers expect subjects as attributes for earlier versions,
        but this new serializer does not have to adhere to that same behavior.

        :param object request: Request object
        :return bool: Subjects should be serialized as relationships
        """
        return True


class DraftRegistrationDetailSerializer(DraftRegistrationSerializer, DraftRegistrationDetailLegacySerializer):
    """
    Overrides DraftRegistrationSerializerLegacy to make id required, and registration_metadata not required.
    registration_supplement, node, cannot be changed after draft has been created.
    """

    registration_metadata = ser.DictField(required=False)

    links = LinksField({
        'self': 'get_self_url',
    })

    def get_self_url(self, obj):
        return absolute_reverse(
            'draft_registrations:draft-registration-detail',
            kwargs={
                'version': self.context['request'].parser_context['kwargs']['version'],
                'draft_id': self.context['request'].parser_context['kwargs']['draft_id'],
            },
        )

    def update(self, draft, validated_data):
        user = self.context['request'].user
        auth = get_user_auth(self.context['request'])

        if 'tags' in validated_data:
            new_tags = set(validated_data.pop('tags', []))
            draft.update_tags(new_tags, auth=auth)
        if 'license_type' in validated_data or 'license' in validated_data:
            license_details = get_license_details(draft, validated_data)
            validated_data['node_license'] = license_details
        if 'affiliated_institutions' in validated_data:
            institutions_list = validated_data.pop('affiliated_institutions')
            new_institutions = [{'_id': institution} for institution in institutions_list]
            update_institutions(draft, new_institutions, user)
        if 'subjects' in validated_data:
            subjects = validated_data.pop('subjects', None)
            self.update_subjects(draft, subjects, auth)

        try:
            draft.update(validated_data, auth=auth)
        except PermissionsError:
            raise exceptions.PermissionDenied
        except DraftRegistrationStateError as e:
            raise InvalidModelValueError(detail=str(e))

        # updates registration_metadata
        return super(DraftRegistrationDetailSerializer, self).update(draft, validated_data)


class DraftRegistrationContributorsSerializer(NodeContributorsSerializer):

    draft_registration = RelationshipField(
        related_view='draft_registrations:draft-registration-detail',
        related_view_kwargs={'draft_id': '<draft_registration._id>'},
    )

    node = HideIfDraft(RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<node._id>'},
    ))

    class Meta:
        type_ = 'contributors'

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'draft_registrations:draft-registration-contributor-detail',
            kwargs={
                'user_id': obj.user._id,
                'draft_id': self.context['request'].parser_context['kwargs']['draft_id'],
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )


class DraftRegistrationContributorsCreateSerializer(NodeContributorsCreateSerializer, DraftRegistrationContributorsSerializer):
    """
    Overrides DraftRegistrationContributorsSerializer to add email, full_name, send_email, and non-required index and users field.

    id and index redefined because of the two serializers we've inherited
    """
    id = IDField(source='_id', required=False, allow_null=True)
    index = ser.IntegerField(required=False, source='_order')

    email_preferences = ['draft_registration', 'false']


class DraftRegistrationContributorDetailSerializer(NodeContributorDetailSerializer, DraftRegistrationContributorsSerializer):
    """
    Overrides NodeContributorDetailSerializer to set the draft registration instead of the node

    id and index redefined because of the two serializers we've inherited
    """
    id = IDField(required=True, source='_id')
    index = ser.IntegerField(required=False, read_only=False, source='_order')