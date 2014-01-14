# -*- coding: utf-8 -*-
import json
import logging

from framework import request
from framework.auth import must_have_session_auth, get_api_key
from ..decorators import must_not_be_registration, must_be_valid_project, must_be_contributor, must_be_contributor_or_public
from framework.forms.utils import process_payload
from framework.mongo.utils import to_mongo
from .node import _view_project

from website.project.metadata.schemas import OSF_META_SCHEMAS

from website.models import MetaSchema
from framework import Q

from .. import clean_template_name

logger = logging.getLogger(__name__)

@must_have_session_auth
@must_be_valid_project
@must_be_contributor # returns user, project
@must_not_be_registration
def node_register_page(*args, **kwargs):

    user = kwargs['user']
    node_to_use = kwargs['node'] or kwargs['project']

    rv = {
        'options': [
            {
                'template_name': metaschema['name'],
                'template_name_clean': clean_template_name(metaschema['name'])
            }
            for metaschema in OSF_META_SCHEMAS
        ]
    }
    rv.update(_view_project(node_to_use, user, primary=True))
    return rv


@must_have_session_auth
@must_be_valid_project
@must_be_contributor_or_public # returns user, project
def node_register_template_page(*args, **kwargs):

    node_to_use = kwargs['node'] or kwargs['project']
    user = kwargs['user']

    template_name = kwargs['template']\
        .replace(' ', '_')

    if node_to_use.is_registration and node_to_use.registered_meta:
        registered = True
        payload = node_to_use.registered_meta.get(to_mongo(template_name))
        if node_to_use.registered_schema:
            meta_schema = node_to_use.registered_schema
        else:
            meta_schema = MetaSchema.find_one(
                Q('name', 'eq', template_name) &
                Q('schema_version', 'eq', 1)
            )
    else:
        registered = False
        payload = None
        meta_schema = MetaSchema.find(
            Q('name', 'eq', template_name)
        ).sort('-schema_version')[0]

    schema = meta_schema.schema

    rv = {
        'template_name': template_name,
        'schema': json.dumps(schema),
        'metadata_version': meta_schema.metadata_version,
        'schema_version': meta_schema.schema_version,
        'registered': registered,
        'payload': payload,
    }
    rv.update(_view_project(node_to_use, user, primary=True))
    return rv


@must_have_session_auth
@must_be_valid_project  # returns project
@must_be_contributor  # returns user, project
@must_not_be_registration
def project_before_register(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    user = kwargs['user']
    api_key = get_api_key()

    prompts = node.callback('before_register', user)

    return {'prompts': prompts}


@must_have_session_auth
@must_be_valid_project
@must_be_contributor # returns user, project
@must_not_be_registration
def node_register_template_page_post(*args, **kwargs):

    node_to_use = kwargs['node'] or kwargs['project']
    user = kwargs['user']
    api_key = kwargs['api_key']

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
    register = node_to_use.register_node(
        schema, user, template, json.dumps(clean_data), api_key
    )

    return {
        'status': 'success',
        'result': register.url,
    }, 201
