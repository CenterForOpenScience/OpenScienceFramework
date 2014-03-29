"""

"""

import os
import logging
import urlparse

from framework.mongo import fields

from website.addons.base import (
    AddonUserSettingsBase, AddonNodeSettingsBase,
    GuidFile
)
from website.util.permissions import READ
from website.addons.base import AddonError

from website.addons.gitlab.api import client, GitlabError
from website.addons.gitlab.utils import (
    setup_user, translate_permissions
)
from website.addons.gitlab import settings as gitlab_settings


logger = logging.getLogger(__name__)


class AddonGitlabUserSettings(AddonUserSettingsBase):

    ########
    # Data #
    ########

    # Account credentials
    user_id = fields.IntegerField()
    username = fields.StringField()

    #############
    # Callbacks #
    #############

    def after_set_password(self, user):
        """Update GitLab password when OSF password changes.

        """
        try:
            client.edituser(self.user_id, encrypted_password=user.password)
        except GitlabError:
            logger.error(
                'Could not set GitLab password for user {0}'.format(
                    user._id
                )
            )


class AddonGitlabNodeSettings(AddonNodeSettingsBase):

    ########
    # Data #
    ########

    creator_osf_id = fields.StringField()
    project_id = fields.IntegerField()
    hook_id = fields.IntegerField()

    @property
    def hook_url(self):
        """Absolute URL for hook callback."""
        relative_url = self.owner.api_url_for(
            'gitlab_hook_callback'
        )
        return urlparse.urljoin(
            gitlab_settings.HOOK_DOMAIN,
            relative_url
        )

    def add_hook(self, save=True):
        if self.hook_id is not None:
            raise AddonError('Hook already exists')
        try:
            status = client.addprojecthook(
                self.project_id,
                self.hook_url
            )
            self.hook_id = status['id']
            if save:
                self.save()
        except GitlabError:
            raise AddonError('Could not add hook')

    def remove_hook(self, save=True):
        if self.hook_id is None:
            raise AddonError('No hook to delete')
        try:
            client.deleteprojecthook(self.project_id, self.hook_id)
            self.hook_id = None
            if save:
                self.save()
        except GitlabError:
            raise AddonError('Could not delete hook')

    #############
    # Callbacks #
    #############

    def after_add_contributor(self, node, added):
        """Add new user to GitLab project.

        """
        user_settings = setup_user(added)
        permissions = node.get_permissions(added)
        print 'PERMISSIONS', permissions
        access_level = translate_permissions(permissions)
        client.addprojectmember(
            self.project_id, user_settings.user_id,
            access_level=access_level
        )

    def after_set_permissions(self, node, user, permissions):
        """Update GitLab permissions.

        """
        if self.project_id is None:
            return
        user_settings = setup_user(user)
        access_level = translate_permissions(permissions)
        client.editprojectmember(
            self.project_id, user_settings.user_id,
            access_level=access_level
        )

    def after_remove_contributor(self, node, removed):
        """Remove user from GitLab project.

        """
        if self.project_id is None:
            return
        user_settings = removed.get_addon('gitlab')
        client.deleteprojectmember(self.project_id, user_settings.user_id)

    def after_fork(self, node, fork, user, save=True):
        """Copy Gitlab project as fork.

        """
        # Call superclass method
        clone, message = super(AddonGitlabNodeSettings, self).after_fork(
            node, fork, user, save=False
        )

        # Get user settings
        user_settings = user.get_or_add_addon('gitlab')

        # Copy project
        try:
            copy = client.createcopy(
                self.project_id, user_settings.user_id, fork._id
            )
            if copy['id'] is None:
                raise AddonError('Could not copy project')
        except GitlabError:
            raise AddonError('Could not copy project')

        clone.project_id = copy['id']

        # Optionally save changes
        if save:
            clone.save()

        return clone, message

    def after_register(self, node, registration, user, save=True):
        """Copy Gitlab project as fork,

        """
        # Call superclass method
        clone, message = super(AddonGitlabNodeSettings, self).after_register(
            node, registration, user, save=False
        )

        # Get user settings
        user_settings = user.get_or_add_addon('gitlab')

        # Copy project
        try:
            copy = client.createcopy(
                self.project_id, user_settings.user_id, registration._id
            )
            if copy['id'] is None:
                raise AddonError('Could not copy project')
        except GitlabError:
            raise AddonError('Could not copy project')

        clone.project_id = copy['id']

        # Grant all contributors read-only permissions
        # TODO: Patch Gitlab so this can be done with one API call
        permission = translate_permissions(READ)
        client.editprojectmember(
            clone.project_id, user_settings.user_id, permission
        )
        for contrib in registration.contributors:
            if contrib == user:
                continue
            contrib_settings = contrib.get_or_add_addon('gitlab')
            client.addprojectmember(
                clone.project_id, contrib_settings.user_id, permission
            )

        # Optionally save changes
        if save:
            clone.save()

        return clone, message

class GitlabGuidFile(GuidFile):

    path = fields.StringField(index=True)

    @property
    def file_url(self):
        if self.path is None:
            raise ValueError('Path field must be defined.')
        return os.path.join('gitlab', 'files', self.path)
