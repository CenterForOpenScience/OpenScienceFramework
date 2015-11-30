# -*- coding: utf-8 -*-
import os
import logging
import httplib as http

from framework.exceptions import HTTPError
from website.util import rubeus

logger = logging.getLogger(__name__)


def is_subdir(path, directory):
    if not (path and directory):
        return False
    # directory is root directory
    if directory == '/':
        return True
    #make both absolute
    abs_directory = os.path.abspath(directory).lower()
    abs_path = os.path.abspath(path).lower()
    return os.path.commonprefix([abs_path, abs_directory]) == abs_directory


def is_authorizer(auth, node_addon):
    """Return if the auth object's user is the same as the authorizer of the node."""
    return auth.user == node_addon.user_settings.owner


def abort_if_not_subdir(path, directory):
    """Check if path is a subdirectory of directory. If not, abort the current
    request with a 403 error.
    """
    if not is_subdir(clean_path(path), clean_path(directory)):
        raise HTTPError(http.FORBIDDEN)
    return True


def get_file_name(path):
    """Given a path, get just the base filename.
    Handles "/foo/bar/baz.txt/" -> "baz.txt"
    """
    return os.path.basename(path.strip('/'))


def clean_path(path):
    """Ensure a path is formatted correctly for url_for."""
    if path is None:
        return ''
    if path == '/':
        return path
    return path.strip('/')


def ensure_leading_slash(path):
    if not path.startswith('/'):
        return '/' + path
    return path


def metadata_to_hgrid(item, node, permissions):
    """Serializes a dictionary of metadata (returned from the DropboxClient)
    to the format expected by Rubeus/HGrid.
    """
    filename = get_file_name(item['path'])
    serialized = {
        'addon': 'dropbox',
        'permissions': permissions,
        'name': get_file_name(item['path']),
        'ext': os.path.splitext(filename)[1],
        rubeus.KIND: rubeus.FOLDER if item['is_dir'] else rubeus.FILE,
        'path': item['path'],
        'urls': {
            'folders': node.api_url_for(
                'dropbox_hgrid_data_contents',
                path=clean_path(item['path']),
            ),
        }
    }
    return serialized


def get_share_folder_uri(path):
    """Return the URI for sharing a folder through the dropbox interface.
    This is not exposed through Dropbox's REST API, so need to build the URI
    "manually".
    """
    cleaned = clean_path(path)
    return ('https://dropbox.com/home/{cleaned}'
            '?shareoptions=1&share_subfolder=0&share=1').format(cleaned=cleaned)


def serialize_folder(metadata):
    """Serializes metadata to a dict with the display name and path
    of the folder.
    """
    # if path is root
    if metadata['path'] == '' or metadata['path'] == '/':
        name = '/ (Full Dropbox)'
    else:
        name = metadata['path']
    return {
        'name': name,
        'path': metadata['path']
    }

def get_folders(client):
    """Gets a list of folders in a user's Dropbox, including the root.
    Each folder is represented as a dict with its display name and path.
    """
    metadata = client.metadata('/', list=True)
    # List each folder, including the root
    root = {
        'name': '/ (Full Dropbox)',
        'path': ''
    }
    folders = [root] + [
        serialize_folder(each)
        for each in metadata['contents'] if each['is_dir']
    ]
    return folders
