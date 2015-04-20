# -*- coding: utf-8 -*-
import json
import httplib as http

from flask import request
from modularodm import Q
from modularodm.exceptions import NoResultsFound, ValidationValueError

from framework import status
from framework.auth import exceptions
from framework.exceptions import HTTPError
from framework.flask import redirect  # VOL-aware redirect

from framework.mongo.utils import to_mongo
from framework.forms.utils import process_payload, unprocess_payload

from website import settings
from website.exceptions import InvalidRetractionApprovalToken, InvalidRetractionDisapprovalToken
from website.project.decorators import (
    must_be_valid_project, must_be_contributor_or_public,
    must_have_permission, must_not_be_registration,
    must_be_public_registration
)
from website.identifiers.model import Identifier
from website.identifiers.metadata import datacite_metadata_for_node
from website.project.metadata.schemas import OSF_META_SCHEMAS
from website.project.utils import serialize_node
from website.util.permissions import ADMIN
from website.models import MetaSchema
from website.models import NodeLog
from website import language, mails

from website.identifiers.client import EzidClient

from .node import _view_project
from .. import clean_template_name


@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def node_register_page(auth, **kwargs):

    node = kwargs['node'] or kwargs['project']

    ret = {
        'options': [
            {
                'template_name': metaschema['name'],
                'template_name_clean': clean_template_name(metaschema['name'])
            }
            for metaschema in OSF_META_SCHEMAS
        ]
    }
    ret.update(_view_project(node, auth, primary=True))
    return ret

@must_be_valid_project
@must_have_permission(ADMIN)
@must_be_public_registration
def node_registration_retraction_get(auth, **kwargs):
    """Prepares node object for registration retraction page.

    :return: serialized Node to be retracted
    :raises: 400: BAD_REQUEST if registration already pending retraction
    """

    node = kwargs['node'] or kwargs['project']
    if node.pending_retraction:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Invalid Request',
            'message_long': 'This registration is already pending a retraction.'
        })

    return serialize_node(node, auth, primary=True)

@must_be_valid_project
@must_have_permission(ADMIN)
@must_be_public_registration
def node_registration_retraction_post(auth, **kwargs):
    """Handles retraction of public registrations

    :param auth: Authentication object for User
    :return: Redirect URL for successful POST
    """

    node = kwargs['node'] or kwargs['project']
    data = request.get_json()

    try:
        node.retract_registration(auth.user, data['justification'])
        node.save()
    except ValidationValueError:
        raise HTTPError(http.BAD_REQUEST)

    # Email project admins
    admins = [contrib for contrib in node.contributors if node.has_permission(contrib, 'admin')]
    for admin in admins:
        _send_retraction_email(
            node,
            admin,
            node.retraction.approval_state[admin._id]['approval_token'],
            node.retraction.approval_state[admin._id]['disapproval_token'],
        )

    return {'redirectUrl': node.web_url_for('view_project')}

def _send_retraction_email(node, user, approval_token, disapproval_token):
    """ Sends Approve/Disapprove email for retraction of a public registration to user
        :param node: Node being retracted
        :param user: Admin user to be emailed
        :param approval_token: token `user` needs to approve retraction
        :param disapproval_token: token `user` needs to disapprove retraction
    """

    base = settings.DOMAIN[:-1]
    registration_link = node.web_url_for('view_project', _absolute=True)
    approval_link = node.web_url_for('node_registration_retraction_approve', token=approval_token, _absolute=True)
    disapproval_link = node.web_url_for('node_registration_retraction_disapprove', token=disapproval_token, _absolute=True)
    approval_time_span = settings.RETRACTION_PENDING_TIME.days * 24


    mails.send_mail(
        user.username,
        mails.PENDING_RETRACTION,
        'plain',
        user=user,
        approval_link=approval_link,
        disapproval_link=disapproval_link,
        registration_link=registration_link,
        approval_time_span=approval_time_span
    )

@must_be_valid_project
@must_have_permission(ADMIN)
@must_be_public_registration
def node_registration_retraction_approve(auth, token, **kwargs):
    """Handles disapproval of registration retractions
    :param auth: User wanting to disapprove retraction
    :return: Redirect to registration or
    :raises: HTTPError if invalid token or user is not admin
    """

    node = kwargs['node'] or kwargs['project']

    if not node.pending_retraction:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Invalid Token',
            'message_long': 'This registration is not pending a retraction.'
        })

    try:
        node.retraction.approve_retraction(auth.user, token)
        node.retraction.save()
    except InvalidRetractionApprovalToken as e:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': e.message_short,
            'message_long': e.message_long
        })
    except ValidationValueError as e:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Unauthorized access',
            'message_long': e.message
        })

    status.push_status_message('Your approval has been accepted.')
    return redirect(node.web_url_for('view_project'))

@must_be_valid_project
@must_have_permission(ADMIN)
@must_be_public_registration
def node_registration_retraction_disapprove(auth, token, **kwargs):
    """Handles approval of registration retractions
    :param auth: User wanting to approve retraction
    :param kwargs:
    :return: Redirect to registration or
    :raises: HTTPError if invalid token or user is not admin
    """

    node = kwargs['node'] or kwargs['project']

    if not node.pending_retraction:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Invalid Token',
            'message_long': 'This registration is not pending a retraction.'
        })

    try:
        node.retraction.disapprove_retraction(auth.user, token)
        node.retraction.save()
    except InvalidRetractionDisapprovalToken as e:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': e.message_short,
            'message_long': e.message_long
        })
    except ValidationValueError as e:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Unauthorized access',
            'message_long': e.message
        })

    status.push_status_message('Your disapproval has been accepted and the retraction has been cancelled.')
    return redirect(node.web_url_for('view_project'))

@must_be_valid_project
@must_be_contributor_or_public
def node_register_template_page(auth, **kwargs):

    node = kwargs['node'] or kwargs['project']

    template_name = kwargs['template'].replace(' ', '_')
    # Error to raise if template can't be found
    not_found_error = HTTPError(
        http.NOT_FOUND,
        data=dict(
            message_short='Template not found.',
            message_long='The registration template you entered '
                         'in the URL is not valid.'
        )
    )

    if node.is_registration and node.registered_meta:
        registered = True
        payload = node.registered_meta.get(to_mongo(template_name))
        payload = json.loads(payload)
        payload = unprocess_payload(payload)

        if node.registered_schema:
            meta_schema = node.registered_schema
        else:
            try:
                meta_schema = MetaSchema.find_one(
                    Q('name', 'eq', template_name) &
                    Q('schema_version', 'eq', 1)
                )
            except NoResultsFound:
                raise not_found_error
    else:
        # Anyone with view access can see this page if the current node is
        # registered, but only admins can view the registration page if not
        # TODO: Test me @jmcarp
        if not node.has_permission(auth.user, ADMIN):
            raise HTTPError(http.FORBIDDEN)
        registered = False
        payload = None
        metaschema_query = MetaSchema.find(
            Q('name', 'eq', template_name)
        ).sort('-schema_version')
        if metaschema_query:
            meta_schema = metaschema_query[0]
        else:
            raise not_found_error
    schema = meta_schema.schema

    # TODO: Notify if some components will not be registered

    ret = {
        'template_name': template_name,
        'schema': json.dumps(schema),
        'metadata_version': meta_schema.metadata_version,
        'schema_version': meta_schema.schema_version,
        'registered': registered,
        'payload': payload,
        'children_ids': node.nodes._to_primary_keys(),
    }
    ret.update(_view_project(node, auth, primary=True))
    return ret


@must_be_valid_project  # returns project
@must_have_permission(ADMIN)
@must_not_be_registration
def project_before_register(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    user = auth.user

    prompts = node.callback('before_register', user=user)

    if node.has_pointers_recursive:
        prompts.append(
            language.BEFORE_REGISTER_HAS_POINTERS.format(
                category=node.project_or_component
            )
        )

    return {'prompts': prompts}


@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def node_register_template_page_post(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    data = request.json

    # Sanitize payload data
    clean_data = process_payload(data)

    template = kwargs['template']
    # TODO: Using json.dumps because node_to_use.registered_meta's values are
    # expected to be strings (not dicts). Eventually migrate all these to be
    # dicts, as this is unnecessary
    schema = MetaSchema.find(
        Q('name', 'eq', template)
    ).sort('-schema_version')[0]
    register = node.register_node(
        schema, auth, template, json.dumps(clean_data),
    )

    return {
        'status': 'success',
        'result': register.url,
    }, http.CREATED


def _build_ezid_metadata(node):
    """Build metadata for submission to EZID using the DataCite profile. See
    http://ezid.cdlib.org/doc/apidoc.html for details.
    """
    doi = settings.EZID_FORMAT.format(namespace=settings.DOI_NAMESPACE, guid=node._id)
    metadata = {
        '_target': node.absolute_url,
        'datacite': datacite_metadata_for_node(node=node, doi=doi)
    }
    return doi, metadata


def _get_or_create_identifiers(node):
    """
    Note: ARKs include a leading slash. This is stripped here to avoid multiple
    consecutive slashes in internal URLs (e.g. /ids/ark/<ark>/). Frontend code
    that build ARK URLs is responsible for adding the leading slash.
    """
    doi, metadata = _build_ezid_metadata(node)
    client = EzidClient(settings.EZID_USERNAME, settings.EZID_PASSWORD)
    try:
        resp = client.create_identifier(doi, metadata)
        return dict(
            [each.strip('/') for each in pair.strip().split(':')]
            for pair in resp['success'].split('|')
        )
    except HTTPError as error:
        if 'identifier already exists' not in error.message.lower():
            raise
        resp = client.get_identifier(doi)
        doi = resp['success']
        suffix = doi.strip(settings.DOI_NAMESPACE)
        return {
            'doi': doi.replace('doi:', ''),
            'ark': '{0}{1}'.format(settings.ARK_NAMESPACE.replace('ark:', ''), suffix),
        }


@must_be_valid_project
@must_be_contributor_or_public
def node_identifiers_get(**kwargs):
    """Retrieve identifiers for a node. Node must be a public registration.
    """
    node = kwargs['node'] or kwargs['project']
    if not node.is_registration or not node.is_public:
        raise HTTPError(http.BAD_REQUEST)
    return {
        'doi': node.get_identifier_value('doi'),
        'ark': node.get_identifier_value('ark'),
    }


@must_be_valid_project
@must_have_permission(ADMIN)
def node_identifiers_post(auth, **kwargs):
    """Create identifier pair for a node. Node must be a public registration.
    """
    node = kwargs['node'] or kwargs['project']
    # TODO: Fail if `node` is retracted
    if not node.is_registration or not node.is_public:  # or node.is_retracted:
        raise HTTPError(http.BAD_REQUEST)
    if node.get_identifier('doi') or node.get_identifier('ark'):
        raise HTTPError(http.BAD_REQUEST)
    try:
        identifiers = _get_or_create_identifiers(node)
    except HTTPError:
        raise HTTPError(http.BAD_REQUEST)
    for category, value in identifiers.iteritems():
        node.set_identifier_value(category, value)
    node.add_log(
        NodeLog.EXTERNAL_IDS_ADDED,
        params={
            'project': node.parent_id,
            'node': node._id,
            'identifiers': identifiers,
        },
        auth=auth,
    )
    return identifiers, http.CREATED


def get_referent_by_identifier(category, value):
    """Look up identifier by `category` and `value` and redirect to its referent
    if found.
    """
    try:
        identifier = Identifier.find_one(
            Q('category', 'eq', category) &
            Q('value', 'eq', value)
        )
    except NoResultsFound:
        raise HTTPError(http.NOT_FOUND)
    if identifier.referent.url:
        return redirect(identifier.referent.url)
    raise HTTPError(http.NOT_FOUND)
