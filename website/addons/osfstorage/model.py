from __future__ import division
from __future__ import unicode_literals

import os
import bson
import logging
from datetime import datetime

import furl
import hurry.filesize

from modularodm import fields, Q
from dateutil.parser import parse as parse_date
from modularodm.exceptions import NoResultsFound
from modularodm.storage.base import KeyExistsException

from framework.mongo import StoredObject
from framework.mongo.utils import unique_on
from framework.analytics import get_basic_counters

from website import mails
from website.addons.base import GuidFile
from website.addons.base import StorageAddonBase
from website.addons.base import AddonNodeSettingsBase
from website.addons.base import AddonUserSettingsBase

from website.addons.osfstorage import utils
from website.addons.osfstorage import errors
from website.addons.osfstorage import settings


logger = logging.getLogger(__name__)


class OsfStorageUserSettings(AddonUserSettingsBase):
    # The current storage being used by this user (in osfstorage) in bytes
    _storage_usage = fields.IntegerField(default=0)
    # The max amount of storage this user may use
    # Overrides the property storage_limit if defined
    storage_limit_override = fields.IntegerField(default=None)

    warning_sent = fields.BooleanField(default=False)
    warning_last_sent = fields.DateTimeField(default=None)

    @property
    def storage_usage(self):
        return self._storage_usage

    @storage_usage.setter
    def storage_usage(self, val):
        """Wraps _storage_usage to keep compatablity w/ the Nodes implementation.
        When _storage_usage goes below the threshold warning_sent will be changed to reflect that.

        Handles Users that keep going above and below their threshold
            1. User exceeds threshold
            2. User recieves warning email
            3. User deletes files; goes below threshold
            4. User exceeds threshold again (within a week)
            5. User should NOT recieve an email
        """
        self._storage_usage = val
        self.warning_sent = self.warning_sent and self.at_warning_threshold

    @property
    def storage_limit(self):
        return self.storage_limit_override or settings.DEFAULT_STORAGE_LIMIT

    @property
    def free_space(self):
        """The amount of space the user has left to use. In bytes.
        """
        return self.storage_limit - self._storage_usage

    @property
    def at_warning_threshold(self):
        """Returns True if the users free space is less than a threshold.
        Used to see if a warning email should be sent to the end user.
        """
        return self.free_space < settings.WARNING_EMAIL_THRESHOLD

    def send_warning_email(self, force=False, save=True):
        """Send out a warning email to the user saying they only have X space left.
        Will not send if recieved_warning is True or warning_last_sent less than a week ago to avoid spamming the user.
        """
        sent_within_week = self.warning_last_sent is not None and datetime.now() - self.warning_last_sent < settings.WARNING_EMAIL_WAITING_PERIOD

        if force or (not self.warning_sent and not sent_within_week):
            mails.send_mail(
                self.owner,
                mails.OSFSTORAGE_USAGE_WARNING,
                fullname=self.owner.fullname,
                used_space=hurry.filesize.size(self.storage_usage, system=hurry.filesize.alternative),
                total_space=hurry.filesize.size(self.storage_limit, system=hurry.filesize.alternative)
            )
            self.warning_sent = True
            self.warning_last_sent = datetime.now()
            if save:
                self.save()

    def update_storage_limit(self, new_limit, save=True):
        """Helper for updating storage_limit_override.
        Use only in the shell, handles checking if the warning email
        flag needs to be reset.
        """
        self.storage_limit_override = new_limit
        if not self.at_warning_threshold:
            self.warning_sent = False
        if save:
            self.save()

    def merge(self, other_user_settings):
        """Merge other_user_settings into self.
        Swaps the all fileversions created by other.owner to self.owner
        Sums the storage_limit of bother other and self into self
        Recalculates storage usage for self
        """
        assert self.__class__ == other_user_settings.__class__

        self.update_storage_limit(self.storage_limit + other_user_settings.storage_limit)

        for file_node in OsfStorageFileVersion.find(Q('creator', 'eq', other_user_settings.owner)):
            file_node.creator = self.owner
            file_node.save()

        self.calculate_storage_usage(save=True)

    def calculate_storage_usage(self, dedup=True, ignored=False, deleted=False, save=False):
        """Calculate the storage being used by this user

        :param bool save: Save the collected value to the user object
        :param bool dedup: Deduplicate based on object location aka sha256
        :param bool deleted: Whether or not to take deleted files/versions into account
        :param bool ignored: Whether or not to take versions where ignore_size == True into account
        :rtype: int
        :raises AssertionError: If save is True and other kwargs are specified
        :returns: The total collected storage usaging of this user in bytes
        """
        q = Q('creator', 'eq', self.owner)

        if not ignored:
            q &= Q('ignore_size', 'eq', False)

        if not deleted:
            q &= Q('deleted', 'eq', False)

        dedupper = (lambda x: {e.location_hash: e for e in x}.values()) if dedup else iter

        usage = sum(
            version.size
            for version in
            dedupper(OsfStorageFileVersion.find(q))
        )

        if save:
            assert dedup and not (ignored or deleted), 'Can only save if dedup is True and ignored and deleted are False'
            self.storage_usage = usage
            self.save()

        return usage

    def calculate_collaborative_usage(self, dedup=True, ignored=False, deleted=False):
        """Collects the collaborative usage of the given user
        Defined as the total usage of all nodes were they have >= write access
        :param bool ignored: Passed to OsfStorageNodeSettings.calculate_storage_usage
        :param bool deleted: Passed to OsfStorageNodeSettings.calculate_storage_usage
        :rtype: int
        """
        node_settings = [
            node.get_addon('osfstorage')
            for node in self.owner.node__contributed
            if node.can_edit(user=self.owner)  # Only include nodes with write access or >
        ]
        return sum(
            # Recurse is false to avoid hitting the same nodes
            # Dont save as recurse is false
            ns.calculate_storage_usage(dedup=dedup, ignored=ignored, deleted=deleted)
            for ns in node_settings
        )

    def __repr__(self):
        return '<{}({!r}, Using {:.2f}%)>'.format(self.__class__.__name__, self.owner, self.storage_usage / self.storage_limit * 100)


class OsfStorageNodeSettings(StorageAddonBase, AddonNodeSettingsBase):
    complete = True
    has_auth = True

    root_node = fields.ForeignField('OsfStorageFileNode')

    # The current storage being used by this user (in osfstorage) in bytes
    storage_usage = fields.IntegerField(default=0)

    @property
    def folder_name(self):
        return self.root_node.name

    def on_add(self):
        if self.root_node:
            return

        # A save is required here to both create and attach the root_node
        # When on_add is called the model that self refers to does not yet exist
        # in the database and thus odm cannot attach foreign fields to it
        self.save()
        # Note: The "root" node will always be "named" empty string
        root = OsfStorageFileNode(name='', kind='folder', node_settings=self)
        root.save()
        self.root_node = root
        self.save()

    def find_or_create_file_guid(self, path):
        return OsfStorageGuidFile.get_or_create(self.owner, path)

    def after_fork(self, node, fork, user, save=True):
        clone = self.clone()
        clone.owner = fork
        clone.save()
        if not self.root_node:
            self.on_add()

        clone.root_node = utils.copy_files(self.root_node, clone)
        clone.save()

        return clone, None

    def after_register(self, node, registration, user, save=True):
        clone = self.clone()
        clone.owner = registration
        clone.on_add()
        clone.save()

        return clone, None

    def serialize_waterbutler_settings(self):
        return dict(settings.WATERBUTLER_SETTINGS, **{
            'nid': self.owner._id,
            'rootId': self.root_node._id,
            'baseUrl': self.owner.api_url_for(
                'osfstorage_get_metadata',
                _absolute=True,
            )
        })

    def serialize_waterbutler_credentials(self):
        return settings.WATERBUTLER_CREDENTIALS

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for(
            'addon_view_or_download_file',
            path=metadata['path'],
            provider='osfstorage'
        )

        self.owner.add_log(
            'osf_storage_{0}'.format(action),
            auth=auth,
            params={
                'node': self.owner._id,
                'project': self.owner.parent_id,

                'path': metadata['materialized'],

                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                },
            },
        )

    def calculate_storage_usage(self, dedup=True, ignored=False, deleted=False, recurse=False, save=False):
        """Calculate the storage being used by this node

        :param bool save: Save the collected value to the node object
        :param bool dedup: Deduplicate based on object location aka sha256
        :param bool recurse: Whether or not to recurse into child nodes
        :param bool deleted: Whether or not to take deleted files/versions into account
        :param bool ignored: Whether or not to take versions where ignore_size == True into account
        :rtype: int
        :returns: The total collected storage usaging of this node in bytes
        :raises AssertionError: If save is True and other kwargs are specified
        """
        dedupper = (lambda x: {e.location_hash: e for e in x}.values()) if dedup else iter

        versions = sum([
            # Must iterate over the list to actually load versions
            # Otherwise they are strings
            [x for x in dedupper(file_node.versions)] for
            file_node in
            OsfStorageFileNode.find(Q('node_settings', 'eq', self))
        ], [])

        if deleted:
            versions.extend(sum([
                # Must iterate over the list to actually load versions
                # Otherwise they are strings
                [x for x in dedupper(file_node.versions)] for
                file_node in
                OsfStorageTrashedFileNode.find(Q('node_settings', 'eq', self))
            ], []))

        usage = sum(
            version.size
            for version in versions
            if (deleted or not version.deleted)
            and (ignored or not version.ignore_size)
        )

        if recurse:
            usage += sum(
                node.get_addon('osfstorage').calculate_storage_usage(
                    ignored=ignored,
                    deleted=deleted,
                    recurse=recurse,
                    save=save
                )
                for node in self.owner.nodes
            )

        if save:
            assert dedup and not (ignored or deleted), 'Can only save if dedup is True and ignored and deleted are False'
            self.storage_usage = usage
            self.save()

        return usage


@unique_on(['name', 'kind', 'parent', 'node_settings'])
class OsfStorageFileNode(StoredObject):
    """A node in the file tree of a given project
    Contains  references to a fileversion and stores information about
    deletion status and position in the tree

               root
              / | \
        child1  |  child3
                child2
                /
            grandchild1
    """

    _id = fields.StringField(primary=True, default=lambda: str(bson.ObjectId()))

    is_deleted = fields.BooleanField(default=False)
    name = fields.StringField(required=True, index=True)
    kind = fields.StringField(required=True, index=True)
    parent = fields.ForeignField('OsfStorageFileNode', index=True)
    versions = fields.ForeignField('OsfStorageFileVersion', list=True)
    node_settings = fields.ForeignField('OsfStorageNodeSettings', required=True, index=True)

    @classmethod
    def create_child_by_path(cls, path, node_settings):
        """Attempts to create a child node from a path formatted as
        /parentid/child_name
        or
        /parentid/child_name/
        returns created, child_node
        """
        try:
            parent_id, child_name = path.strip('/').split('/')
            parent = cls.get_folder(parent_id, node_settings)
        except ValueError:
            try:
                parent, (child_name, ) = node_settings.root_node, path.strip('/').split('/')
            except ValueError:
                raise errors.InvalidPathError('Path {} is invalid'.format(path))

        try:
            if path.endswith('/'):
                return True, parent.append_folder(child_name)
            else:
                return True, parent.append_file(child_name)
        except KeyExistsException:
            if path.endswith('/'):
                return False, parent.find_child_by_name(child_name, kind='folder')
            else:
                return False, parent.find_child_by_name(child_name, kind='file')

    @classmethod
    def get(cls, path, node_settings):
        path = path.strip('/')

        if not path:
            return node_settings.root_node

        return cls.find_one(
            Q('_id', 'eq', path) &
            Q('node_settings', 'eq', node_settings)
        )

    @classmethod
    def get_folder(cls, path, node_settings):
        path = path.strip('/')

        if not path:
            return node_settings.root_node

        return cls.find_one(
            Q('_id', 'eq', path) &
            Q('kind', 'eq', 'folder') &
            Q('node_settings', 'eq', node_settings)
        )

    @classmethod
    def get_file(cls, path, node_settings):
        return cls.find_one(
            Q('_id', 'eq', path.strip('/')) &
            Q('kind', 'eq', 'file') &
            Q('node_settings', 'eq', node_settings)
        )

    @property
    @utils.must_be('folder')
    def children(self):
        return self.__class__.find(Q('parent', 'eq', self._id))

    @property
    def is_folder(self):
        return self.kind == 'folder'

    @property
    def is_file(self):
        return self.kind == 'file'

    @property
    def path(self):
        return '/{}{}'.format(self._id, '/' if self.is_folder else '')

    @property
    def node(self):
        return self.node_settings.owner

    def materialized_path(self):
        """creates the full path to a the given filenode
        Note: Possibly high complexity/ many database calls
        USE SPARINGLY
        """
        if not self.parent:
            return '/'
        # Note: ODM cache can be abused here
        # for highly nested folders calling
        # list(self.__class__.find(Q(nodesetting),Q(folder))
        # may result in a massive increase in performance
        def lineage():
            current = self
            while current:
                yield current
                current = current.parent

        path = os.path.join(*reversed([x.name for x in lineage()]))
        if self.is_folder:
            return '/{}/'.format(path)
        return '/{}'.format(path)

    @utils.must_be('folder')
    def find_child_by_name(self, name, kind='file'):
        return self.__class__.find_one(
            Q('name', 'eq', name) &
            Q('kind', 'eq', kind) &
            Q('parent', 'eq', self)
        )

    def append_folder(self, name, save=True):
        return self._create_child(name, 'folder', save=save)

    def append_file(self, name, save=True):
        return self._create_child(name, 'file', save=save)

    @utils.must_be('folder')
    def _create_child(self, name, kind, save=True):
        child = OsfStorageFileNode(
            name=name,
            kind=kind,
            parent=self,
            node_settings=self.node_settings
        )
        if save:
            child.save()
        return child

    def get_download_count(self, version=None):
        if self.is_folder:
            return None

        parts = ['download', self.node._id, self._id]
        if version is not None:
            parts.append(version)
        page = ':'.join([format(part) for part in parts])
        _, count = get_basic_counters(page)

        return count or 0

    @utils.must_be('file')
    def get_version(self, index=-1, required=False):
        try:
            return self.versions[index]
        except IndexError:
            if required:
                raise errors.VersionNotFoundError
            return None

    @utils.must_be('file')
    def create_version(self, creator, location, metadata=None, ignore_size=False):
        """Creates a new OsfStorageFileVersion and pushes it to the head of versions
        :param User creator: The user that created this version
        :param dict location: A dict describing the location of this version
        :param dict metadata: Optional metadata about this version
        :param bool ignore_size: Wether or not to update storage usage on node and creator
        """
        latest_version = self.get_version()
        version = OsfStorageFileVersion(creator=creator, location=location, ignore_size=ignore_size)

        if latest_version and latest_version.is_duplicate(version):
            return latest_version

        if metadata:
            version.update_metadata(metadata)

        version._find_duplicates(save=False)
        version._find_matching_archive(save=False)

        # No if guards, rely on ignore_size on the version
        version.update_storage_usage(save=True)
        version.update_storage_usage(of=self.node_settings, save=True)

        version.save()
        self.versions.append(version)
        self.save()

        return version

    @utils.must_be('file')
    def update_version_metadata(self, location, metadata):
        for version in reversed(self.versions):
            if version.location == location:
                version.update_metadata(metadata)
                return
        raise errors.VersionNotFoundError

    def delete(self, recurse=True, save=True):
        """Moves the given file node to the OsfStorageTrashedFileNode
        collection. Also updates user and node storage usages and optionally
        deleted children.
        :param bool recurse: Whether or not to delete children
        """
        trashed = OsfStorageTrashedFileNode()
        trashed._id = self._id
        trashed.name = self.name
        trashed.kind = self.kind
        trashed.parent = self.parent
        trashed.versions = self.versions
        trashed.node_settings = self.node_settings

        trashed.save()

        for version in self.versions:
            version.deleted = True
            # Dont include deleted versions in future calculations
            version.update_storage_usage(save=True)
            version.update_storage_usage(of=self.node_settings)

            version.save()

        if self.is_folder and recurse:
            for child in self.children:
                child.delete(save=False)

        self.node_settings.save()
        self.__class__.remove_one(self)

    def serialized(self, include_full=False):
        """Build Treebeard JSON for folder or file.
        """
        data = {
            'id': self._id,
            'path': self.path,
            'name': self.name,
            'kind': self.kind,
        }

        if include_full:
            data['fullPath'] = self.materialized_path()

        if self.is_folder:
            return data

        version = self.get_version()

        data.update({
            'version': len(self.versions),
            'downloads': self.get_download_count(),
            'size': version.size if version else None,
            'contentType': version.content_type if version else None,
            'modified': version.date_modified.isoformat() if version and version.date_modified else None,
        })
        return data

    def copy_under(self, destination_parent, name=None):
        return utils.copy_files(self, destination_parent.node_settings, destination_parent, name=name)

    def move_under(self, destination_parent, name=None):
        self.name = name or self.name
        self.parent = destination_parent
        self._update_node_settings(save=True)
        # Trust _update_node_settings to save us

        return self

    def _update_node_settings(self, recursive=True, save=True):
        if self.parent is not None:
            self.node_settings = self.parent.node_settings
        if save:
            self.save()
        if recursive and self.is_folder:
            for child in self.children:
                child._update_node_settings(save=save)

    def __repr__(self):
        return '<{}(name={!r}, node_settings={!r})>'.format(
            self.__class__.__name__,
            self.name,
            self.to_storage()['node_settings']
        )


class OsfStorageFileVersion(StoredObject):
    """A version of an OsfStorageFileNode. contains information
    about where the file is located, hashes and datetimes
    """

    _id = fields.StringField(primary=True, default=lambda: str(bson.ObjectId()))
    creator = fields.ForeignField('user', required=True)

    # Date version record was created. This is the date displayed to the user.
    date_created = fields.DateTimeField(auto_now_add=True)

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

    # If this version's parent FileNode has been deleted
    deleted = fields.BooleanField(default=False)
    # Indicates if this file version has a duplicate elsewhere in the database
    # If one variant's has_duplicate is True then all has_duplicates will be True
    # duplicates are defined as have the same value for object and creator
    has_duplicate = fields.BooleanField(default=False)
    # If set to True the size of this version will be ignored
    # when calculating the the storage usage of both nodes and users
    # IE Files that are part of a registration or provided pro bono
    ignore_size = fields.BooleanField(default=False)

    @property
    def location_hash(self):
        return self.location['object']

    @property
    def archive(self):
        return self.metadata.get('archive')

    def is_duplicate(self, other):
        return self.location_hash == other.location_hash

    def update_metadata(self, metadata):
        self.metadata.update(metadata)

        # metadata has no defined structure so only attempt to set attributes
        # If its are not in this callback it'll be in the next
        if self.metadata.get('size') is not None:
            self.size = int(self.metadata['size'])

        self.content_type = self.metadata.get('contentType', self.content_type)

        if 'modified' in self.metadata:
            # TODO handle the timezone here the user that updates the file may see an
            # Incorrect version
            self.date_modified = parse_date(self.metadata['modified'], ignoretz=True)
        self.save()

    def update_storage_usage(self, of=None, save=True):
        """Increments or decrements the `storage_usage` attribute of `of`
        :param modm.StoredObject of: The model to be updated, if `None` defaults to self.creator's osfstorage addon
        :param bool deleted: Increment if True decrement if False
        :param bool save: Whether or not to save the model after
        """
        # Dont update any fields if we're ignoring size
        if self.ignore_size:
            return

        # If there are non-deleted duplicates dont update anything
        if self.has_duplicate:
            dups = self.__class__.find(
                Q('_id', 'ne', self._id) &
                Q('deleted', 'eq', False) &
                Q('ignore_size', 'eq', False) &
                Q('creator', 'eq', self.creator) &
                Q('location.object', 'eq', self.location_hash)
            )
            if dups.count() > 0:
                return

        of = of or self.creator.get_addon('osfstorage')
        if self.deleted:
            of.storage_usage -= self.size
        else:
            of.storage_usage += self.size
        if save:
            of.save()
        return of.storage_usage

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

    def _find_duplicates(self, save=True):
        dups = self.__class__.find(
            Q('_id', 'ne', self._id) &
            Q('deleted', 'eq', False) &
            Q('ignore_size', 'eq', False) &
            Q('creator', 'eq', self.creator) &
            Q('location.object', 'eq', self.location_hash)
        )
        if dups.count() < 1:
            return
        # If there is only one other duplicate it's flag
        # has not been set
        if dups.count() == 1:
            dups[0].has_duplicate = True
            dups[0].save()
        self.has_duplicate = True
        if save:
            self.save()

@unique_on(['node', 'path'])
class OsfStorageGuidFile(GuidFile):
    """A reference back to a OsfStorageFileNode

    path is the "waterbutler path" as well as the path
    used to look up a filenode

    GuidFile.path == FileNode.path == '/' + FileNode._id
    """

    path = fields.StringField(required=True, index=True)
    provider = 'osfstorage'
    version_identifier = 'version'

    _path = fields.StringField(index=True)
    premigration_path = fields.StringField(index=True)
    path = fields.StringField(required=True, index=True)

    # Marker for invalid GUIDs that are associated with a node but not
    # part of a GUID's file tree, e.g. those generated by spiders
    _has_no_file_tree = fields.BooleanField(default=False)

    @classmethod
    def get_or_create(cls, node, path):
        try:
            return cls.find_one(
                Q('node', 'eq', node) &
                Q('path', 'eq', path)
            ), False
        except NoResultsFound:
            # Create new
            new = cls(node=node, path=path)
            new.save()
        return new, True

    @property
    def waterbutler_path(self):
        return self.path

    @property
    def unique_identifier(self):
        return self._metadata_cache['extra']['version']

    @property
    def file_url(self):
        return os.path.join('osfstorage', 'files', self.path.lstrip('/'))

    def get_download_path(self, version_idx):
        url = furl.furl('/{0}/'.format(self._id))
        url.args.update({
            'action': 'download',
            'version': version_idx,
            'mode': 'render',
        })
        return url.url


class OsfStorageTrashedFileNode(StoredObject):
    """The graveyard for all deleted OsfStorageFileNodes"""
    _id = fields.StringField(primary=True)
    name = fields.StringField(required=True, index=True)
    kind = fields.StringField(required=True, index=True)
    parent = fields.ForeignField('OsfStorageFileNode', index=True)
    versions = fields.ForeignField('OsfStorageFileVersion', list=True)
    node_settings = fields.ForeignField('OsfStorageNodeSettings', required=True, index=True)
