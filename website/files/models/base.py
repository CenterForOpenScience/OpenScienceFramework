from __future__ import unicode_literals

import os
import bson
import logging
import requests

from modularodm import fields, Q
from modularodm.exceptions import NoResultsFound
from dateutil.parser import parse as parse_date

from framework.guid.model import Guid
from framework.mongo import StoredObject
from framework.mongo.utils import unique_on
from framework.analytics import get_basic_counters

from website import util
from website.files import utils
from website.files import exceptions


__all__ = (
    'File',
    'Folder',
    'FileNode',
    'FileVersion',
    'StoredFileNode',
    'TrashedFileNode',
)


PROVIDER_MAP = {}
logger = logging.getLogger(__name__)


class TrashedFileNode(StoredObject):
    """The graveyard for all deleted FileNodes"""
    _id = fields.StringField(primary=True)

    versions = fields.ForeignField('FileVersion', list=True)

    node = fields.ForeignField('node', required=True)
    parent = fields.AbstractForeignField(default=None)

    is_file = fields.BooleanField(default=True)
    provider = fields.StringField(required=True)

    name = fields.StringField(required=True)
    path = fields.StringField(required=True)
    materialized_path = fields.StringField(required=True)


@unique_on(['node', 'name', 'parent', 'is_file', 'provider', 'materialized_path'])
class StoredFileNode(StoredObject):
    """The storage backend for FileNode objects.
    This class should generally not be used or created manually as FileNode
    contains all the helpers required.
    A FileNode wraps a StoredFileNode to provider usable abstraction layer
    """
    _id = fields.StringField(primary=True, default=lambda: str(bson.ObjectId()))

    versions = fields.ForeignField('FileVersion', list=True)

    node = fields.ForeignField('Node', required=True)
    parent = fields.ForeignField('StoredFileNode', default=None)

    is_file = fields.BooleanField(default=True)
    provider = fields.StringField(required=True)

    name = fields.StringField(required=True)
    path = fields.StringField(required=True)
    materialized_path = fields.StringField(required=True)

    @property
    def deep_url(self):
        return self.wrapped().deep_url

    def wrapped(self):
        """Wrap self in a FileNode subclass
        """
        return PROVIDER_MAP[self.provider][int(self.is_file)](self)

    def get_guid(self, create=False):
        """Attempt to find a Guid that points to this object.
        One will be created if requested.
        :rtype: Guid
        """
        try:
            return Guid.find_one(Q('referent', 'eq', self))
        except NoResultsFound:
            if not create:
                return None
        return Guid.generate(self)


class FileNodeMeta(type):
    """Keeps track of subclasses of the ``FileNode`` object
    Inserts all into the PROVIDER_MAP following the pattern:
    {
        provider: [ProviderFolder, ProviderFile, ProviderFileNode]
    }
    """

    def __init__(cls, name, bases, dct):
        super(FileNodeMeta, cls).__init__(name, bases, dct)
        if hasattr(cls, 'provider'):
            cls_map = PROVIDER_MAP.setdefault(cls.provider, [None, None, None])
            index = int(getattr(cls, 'is_file', 2))

            if cls_map[index] is not None:
                raise ValueError('Conflicting providers')

            cls_map[index] = cls


class FileNode(object):
    """The base class for the entire files storage system.
    Use for querying on all files and folders in the database
    """
    FOLDER, FILE, ANY = 0, 1, 2

    __metaclass__ = FileNodeMeta

    @classmethod
    def create(cls, **kwargs):
        """A layer of abstraction around the creation of FileNodes.
        Provides hook in points for subclasses
        This is used only for GUID creation.
        """
        assert hasattr(cls, 'is_file') and hasattr(cls, 'provider'), 'Must have is_file and provider to call create'
        kwargs['is_file'] = cls.is_file
        kwargs['provider'] = cls.provider
        return cls(**kwargs)

    @classmethod
    def get_or_create(cls, node, path):
        """Tries to find a FileNode with node and path
        See FileNode.create
        """
        path = '/' + path.lstrip('/')
        try:
            return cls.find_one(
                Q('node', 'eq', node) &
                Q('path', 'eq', path)
            )
        except NoResultsFound:
            return cls.create(node=node, path=path)

    @classmethod
    def resolve_class(cls, provider, _type=2):
        """Resolves a provider and type to the appropriate subclass.
        Usage:
            >>> FileNode.resolve_class('box', FileNode.ANY)  # BoxFileNode
            >>> FileNode.resolve_class('dropbox', FileNode.FILE)  # DropboxFile
        :rtype: Subclass of FileNode
        """
        return PROVIDER_MAP[provider][int(_type)]

    @classmethod
    def _filter(cls, qs=None):
        """Creates an odm query to limit the scope of whatever search method
        to the given class.
        :param qs RawQuery: An odm query or None
        :rtype: RawQuery or None
        """
        # Build a list of all possible contraints leaving None when appropriate
        # filter(None, ...) removes all falsey values
        qs = filter(None, (qs,
            Q('is_file', 'eq', cls.is_file) if hasattr(cls, 'is_file') else None,
            Q('provider', 'eq', cls.provider) if hasattr(cls, 'provider') else None,
        ))
        # If out list is empty return None; there's no filters to be applied
        if not qs:
            return None
        # Use reduce to & together all our queries. equavilent to:
        # return q1 & q2 ... & qn
        return reduce(lambda q1, q2: q1 & q2, qs)

    @classmethod
    def find(cls, qs=None):
        """A proxy for StoredFileNode.find but applies class based contraints.
        Wraps The MongoQuerySet in a _GenWrapper this overrides the __iter__ of
        MongoQuerySet to return wrapped objects
        :rtype: _GenWrapper<MongoQuerySet<cls>>
        """
        return utils._GenWrapper(StoredFileNode.find(cls._filter(qs)))

    @classmethod
    def find_one(cls, qs):
        """A proxy for StoredFileNode.find_one but applies class based contraints.
        :rtype: cls
        """
        return StoredFileNode.find_one(cls._filter(qs)).wrapped()

    @classmethod
    def load(cls, _id):
        """A proxy for StoredFileNode.load requires the wrapped version of the found value
        to be an instance of cls.
        :rtype: cls
        """
        inst = StoredFileNode.load(_id)
        if not inst:
            return None
        inst = inst.wrapped()
        assert isinstance(inst, cls), 'Loaded object {} is not of type {}'.format(inst, cls)
        return inst

    @property
    def parent(self):
        """A proxy to self.stored_object.parent but forces it to be wrapped.
        """
        if self.stored_object.parent:
            return self.stored_object.parent.wrapped()
        return None

    @parent.setter
    def parent(self, val):
        """A proxy to self.stored_object.parent but will unwrap it when need be
        """
        if isinstance(val, FileNode):
            val = val.stored_object
        self.stored_object.parent = val

    @property
    def deep_url(self):
        """The url that this filenodes guid should resolve to.
        Implemented here so that subclasses may override it; see dropbox
        """
        return self.node.web_url_for('addon_view_or_download_file', provider=self.provider, path=self.path.strip('/'))

    def __init__(self, *args, **kwargs):
        """Contructor for FileNode's subclasses
        If called with only a StoredFileNode it will be attached to self
        Otherwise:
        Injects provider and is_file when appropriate.
        Creates a new StoredFileNode with kwargs, not saved.
        Then attaches stored_object to self
        """
        if args and isinstance(args[0], StoredFileNode):
            assert len(args) == 1
            assert len(kwargs) == 0
            self.stored_object = args[0]
        else:
            if hasattr(self, 'provider'):
                kwargs['provider'] = self.provider
            if hasattr(self, 'is_file'):
                kwargs['is_file'] = self.is_file
            self.stored_object = StoredFileNode(*args, **kwargs)

    def save(self):
        """A proxy to self.stored_object.save.
        Implemented top level so that child class may override it
        and just call super.save rather than self.stored_object.save
        """
        self.stored_object.save()

    def kind(self):
        """Whether this FileNode is a file or folder as a string.
        Used for serialization and backwards compatability
        :rtype: str
        :returns: 'file' or 'folder'
        """
        return 'file' if self.is_file else 'folder'

    def serialize(self, **kwargs):
        return {
            'id': self._id,
            'path': self.path,
            'name': self.name,
            'kind': self.kind,
        }

    def generate_metadata_url(self, **kwargs):
        return util.waterbutler_url_for(
            'metadata',
            self.provider,
            self.path,
            self.node,
            **kwargs
        )

    def delete(self):
        """Move self into the TrashedFileNode collection
        and remove it from StoredFileNode
        """
        self.trashed = self._created_trashed()
        StoredFileNode.remove_one(self.stored_object)

    def copy_under(self, destination_parent, name=None):
        return utils.copy_files(self, destination_parent.node, destination_parent, name=name)

    def move_under(self, destination_parent, name=None):
        self.name = name or self.name
        self.parent = destination_parent.stored_object
        self._update_node(save=True)
        # Trust _update_node to save us

        return self

    def _created_trashed(self, save=True):
        trashed = TrashedFileNode()
        trashed._id = self._id
        trashed.name = self.name
        trashed.path = self.path
        trashed.node = self.node
        trashed.parent = self.parent
        trashed.is_file = self.is_file
        trashed.provider = self.provider
        trashed.versions = self.versions
        trashed.materialized_path = self.materialized_path
        if save:
            trashed.save()
        return trashed

    def _update_node(self, recursive=True, save=True):
        if self.parent is not None:
            self.node = self.parent.node
        if save:
            self.save()
        if recursive and not self.is_file:
            for child in self.children:
                child._update_node(save=save)

    def __getattr__(self, name):
        """For the purpose of proxying all calls to the below stored_object
        Saves typing out ~10 properties or so
        """
        if 'stored_object' in self.__dict__:
            try:
                return getattr(self.stored_object, name)
            except AttributeError:
                pass  # Avoids error message about the underlying object
        return object.__getattribute__(self, name)

    def __setattr__(self, name, val):
        # Property setters are called after __setattr__ is called
        # If the requested attribute is a property with a setter go ahead and use it
        maybe_prop = getattr(self.__class__, name, None)
        if isinstance(maybe_prop, property) and maybe_prop.fset is not None:
            return object.__setattr__(self, name, val)
        if 'stored_object' in self.__dict__:
            return setattr(self.stored_object, name, val)
        return object.__setattr__(self, name, val)

    def __eq__(self, other):
        return self.stored_object == getattr(other, 'stored_object', None)

    def __repr__(self):
        return '<{}(name={!r}, node={!r})>'.format(
            self.__class__.__name__,
            self.stored_object.name,
            self.stored_object.node
        )


class File(FileNode):
    is_file = True

    def get_version(self, revision, required=False):
        """Find a version with identifier revision
        :returns: FileVersion or None
        :raises: VersionNotFoundError if required is True
        """
        for version in reversed(self.versions):
            if version.identifier == revision:
                break
        else:
            if required:
                raise exceptions.VersionNotFoundError(revision)
            return None
        return version

    def update_version_metadata(self, location, metadata):
        for version in reversed(self.versions):
            if version.location == location:
                version.update_metadata(metadata)
                return
        raise exceptions.VersionNotFound

    def generate_download_url(self, **kwargs):
        return util.waterbutler_url_for(
            'download',
            self.provider,
            self.path,
            self.node,
            **kwargs
        )

    def touch(self, revision=None, **kwargs):
        """The bread and butter of File, collects metadata about self
        and creates versions and updates self when required.
        If revisions is None the created version is NOT and should NOT be saved
        as there is no identifing information to tell if it needs to be updated or not.
        Hits Waterbutler's metadata endpoint and saves the returned data.
        :returns: None if the file is not found otherwise FileVersion
        """
        version = self.get_version(revision)
        # Versions do not change. No need to refetch what we already know
        if version is not None:
            return version

        resp = requests.get(self.generate_metadata_url(revision=revision, **kwargs))
        if resp.status_code != 200:
            logger.warning('Unable to find {} got status code {}'.format(self, resp.status_code))
            return None

        data = resp.json()
        self.name = data['data']['name']
        self.materialized_path = data['data']['materialized']

        version = FileVersion(identifier=revision)
        version.update_metadata(data['data'], save=False)

        # if revision is none then version is the latest version
        # Dont save the latest information
        if revision is not None:
            version.save()
            self.versions.append(version)

        self.save()
        return version

    def get_download_count(self, version=None):
        """Pull the download count from the pagecounter collection
        Limit to version if specified.
        Currently only useful for OsfStorage
        """
        parts = ['download', self.node._id, self._id]
        if version is not None:
            parts.append(version)
        page = ':'.join([format(part) for part in parts])
        _, count = get_basic_counters(page)

        return count or 0

    def serialize(self):
        return dict(
            super(File, self).serialize(),
            downloads=self.get_download_count(),
            size=self.versions[-1].size if self.versions else None,
            version=self.versions[-1].identifier if self.versions else None,
        )


class Folder(FileNode):
    is_file = False

    @property
    def children(self):
        """Finds all Filenodes that view self as a parent
        :returns: A _GenWrapper for all children
        :rtype: _GenWrapper<MongoQuerySet<cls>>
        """
        return FileNode.find(Q('parent', 'eq', self._id))

    def delete(self, recurse=True):
        self.trashed = self._created_trashed()
        if recurse:
            for child in self.children:
                child.delete()
        StoredFileNode.remove_one(self.stored_object)

    def append_file(self, name, path=None, materialized_path=None, save=True):
        return self._create_child(name, FileNode.FILE, path=path, materialized_path=materialized_path, save=save)

    def append_folder(self, name, path=None, materialized_path=None, save=True):
        return self._create_child(name, FileNode.FOLDER, path=path, materialized_path=materialized_path, save=save)

    def _create_child(self, name, kind, path=None, materialized_path=None, save=True):
        child = PROVIDER_MAP[self.provider][kind](
            name=name,
            node=self.node,
            path=path or '/' + name,
            parent=self.stored_object,
            materialized_path=materialized_path or
            os.path.join(self.materialized_path, name) + '/' if not kind else ''
        ).wrapped()
        if save:
            child.save()
        return child

    def find_child_by_name(self, name, kind=2):
        return PROVIDER_MAP[self.provider][kind].find_one(
            Q('name', 'eq', name) &
            Q('parent', 'eq', self)
        )


class FileVersion(StoredObject):
    """A version of an OsfStorageFileNode. contains information
    about where the file is located, hashes and datetimes
    """

    _id = fields.StringField(primary=True, default=lambda: str(bson.ObjectId()))

    creator = fields.ForeignField('user')

    identifier = fields.StringField(required=True)

    # Date version record was created. This is the date displayed to the user.
    date_created = fields.DateTimeField(auto_now_add=True)
    last_touched = fields.DateTimeField(auto_now_add=True)

    # Dictionary specifying all information needed to locate file on backend
    # {
    #     'service': 'cloudfiles',  # required
    #     'container': 'osf',       # required
    #     'object': '20c53b',       # required
    #     'worker_url': '127.0.0.1',
    #     'worker_host': 'upload-service-1',
    # }
    location = fields.DictionaryField(validate=utils.validate_location)

    # Dictionary containing raw metadata from upload service response
    # {
    #     'size': 1024,                            # required
    #     'content_type': 'text/plain',            # required
    #     'date_modified': '2014-11-07T20:24:15',  # required
    #     'md5': 'd077f2',
    # }
    metadata = fields.DictionaryField()

    size = fields.IntegerField()
    content_type = fields.StringField()
    # Date file modified on third-party backend. Not displayed to user, since
    # this date may be earlier than the date of upload if the file already
    # exists on the backend
    date_modified = fields.DateTimeField()

    @property
    def location_hash(self):
        return self.location['object']

    @property
    def archive(self):
        return self.metadata.get('archive')

    def is_duplicate(self, other):
        return self.location_hash == other.location_hash

    def update_metadata(self, metadata, save=True):
        self.metadata.update(metadata)
        # metadata has no defined structure so only attempt to set attributes
        # If its are not in this callback it'll be in the next
        self.size = self.metadata.get('size', self.size)
        self.content_type = self.metadata.get('contentType', self.content_type)
        if self.metadata.get('modified') is not None:
            # TODO handle the timezone here the user that updates the file may see an
            # Incorrect version
            self.date_modified = parse_date(self.metadata['modified'], ignoretz=True)

        if save:
            self.save()

    def _find_matching_archive(self, save=True):
        """Find another version with the same sha256 as this file.
        If found copy its vault name and glacier id, no need to create additional backups.
        returns True if found otherwise false
        """
        if 'sha256' not in self.metadata:
            return False  # Dont bother searching for nothing

        if 'vault' in self.metadata and 'archive' in self.metadata:
            # Shouldn't ever happen, but we already have an archive
            return True  # We've found ourself

        qs = self.__class__.find(
            Q('_id', 'ne', self._id) &
            Q('metadata.vault', 'ne', None) &
            Q('metadata.archive', 'ne', None) &
            Q('metadata.sha256', 'eq', self.metadata['sha256'])
        ).limit(1)
        if qs.count() < 1:
            return False
        other = qs[0]
        try:
            self.metadata['vault'] = other.metadata['vault']
            self.metadata['archive'] = other.metadata['archive']
        except KeyError:
            return False
        if save:
            self.save()
        return True
