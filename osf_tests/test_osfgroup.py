import pytest

from django.contrib.auth.models import Group

from framework.auth import Auth
from framework.exceptions import PermissionsError
from osf.models import OSFGroup
from .factories import (
    ProjectFactory,
    UserFactory,
    OSFGroupFactory
)

pytestmark = pytest.mark.django_db

@pytest.fixture()
def manager():
    return UserFactory()

@pytest.fixture()
def member():
    return UserFactory()

@pytest.fixture()
def user_two():
    return UserFactory()

@pytest.fixture()
def user_three():
    return UserFactory()

@pytest.fixture()
def auth(manager):
    return Auth(manager)

@pytest.fixture()
def project(manager):
    return ProjectFactory(creator=manager)

@pytest.fixture()
def osf_group(manager, member):
    osf_group = OSFGroupFactory(creator=manager)
    osf_group.make_member(member)
    return osf_group

class TestOSFGroup:

    def test_osf_group_creation(self, manager, member, user_two, fake):
        osf_group = OSFGroup.objects.create(name=fake.bs(), creator=manager)
        # OSFGroup creator given manage permissions
        assert osf_group.has_permission(manager, 'manage') is True
        assert osf_group.has_permission(user_two, 'manage') is False

        assert manager in osf_group.managers
        assert manager in osf_group.members

    def test_make_manager(self, manager, member, user_two, user_three, osf_group):
        # no permissions
        with pytest.raises(PermissionsError):
            osf_group.make_manager(user_two, Auth(user_three))

        # member only
        with pytest.raises(PermissionsError):
            osf_group.make_manager(user_two, Auth(member))

        # manage permissions
        osf_group.make_manager(user_two, Auth(manager))
        assert osf_group.has_permission(user_two, 'manage') is True
        assert user_two in osf_group.managers
        assert user_two in osf_group.members

        # upgrade to manager
        osf_group.make_manager(member, Auth(manager))
        assert osf_group.has_permission(member, 'manage') is True
        assert member in osf_group.managers
        assert member in osf_group.members

    def test_make_member(self, manager, member, user_two, user_three, osf_group):
        # no permissions
        with pytest.raises(PermissionsError):
            osf_group.make_member(user_two, Auth(user_three))

        # member only
        with pytest.raises(PermissionsError):
            osf_group.make_member(user_two, Auth(member))

        # manage permissions
        osf_group.make_member(user_two, Auth(manager))
        assert osf_group.has_permission(user_two, 'manage') is False
        assert user_two not in osf_group.managers
        assert user_two in osf_group.members

        # downgrade to member, sole manager
        with pytest.raises(ValueError):
            osf_group.make_member(manager, Auth(manager))

        # downgrade to member
        osf_group.make_manager(user_two, Auth(manager))
        assert user_two in osf_group.managers
        assert user_two in osf_group.members
        osf_group.make_member(user_two, Auth(manager))
        assert user_two not in osf_group.managers
        assert user_two in osf_group.members

    def test_remove_member(self, manager, member, user_three, osf_group):
        new_member = UserFactory()
        osf_group.make_member(new_member)
        assert new_member not in osf_group.managers
        assert new_member in osf_group.members

        # no permissions
        with pytest.raises(PermissionsError):
            osf_group.remove_member(new_member, Auth(user_three))

        # member only
        with pytest.raises(PermissionsError):
            osf_group.remove_member(new_member, Auth(member))

        # manage permissions
        osf_group.remove_member(new_member, Auth(manager))
        assert new_member not in osf_group.managers
        assert new_member not in osf_group.members

        # Attempt to remove manager using this method
        osf_group.make_manager(user_three)
        with pytest.raises(ValueError):
            osf_group.remove_member(user_three)

        # Remove self - member can remove themselves
        osf_group.remove_member(member, Auth(member))
        assert member not in osf_group.managers
        assert member not in osf_group.members

    def test_remove_manager(self, manager, member, user_three, osf_group):
        new_manager = UserFactory()
        osf_group.make_manager(new_manager)
        # no permissions
        with pytest.raises(PermissionsError):
            osf_group.remove_manager(new_manager, Auth(user_three))

        # member only
        with pytest.raises(PermissionsError):
            osf_group.remove_manager(new_manager, Auth(member))

        # manage permissions
        osf_group.remove_manager(new_manager, Auth(manager))
        assert new_manager not in osf_group.managers
        assert new_manager not in osf_group.members

        # can't remove last manager
        with pytest.raises(ValueError):
            osf_group.remove_manager(manager, Auth(manager))
        assert manager in osf_group.managers
        assert manager in osf_group.members

    def test_rename_osf_group(self, manager, member, user_two, osf_group):
        new_name = 'Platform Team'
        # no permissions
        with pytest.raises(PermissionsError):
            osf_group.set_group_name(new_name, Auth(user_two))

        # member only
        with pytest.raises(PermissionsError):
            osf_group.set_group_name(new_name, Auth(member))

        # manage permissions
        osf_group.set_group_name(new_name, Auth(manager))
        osf_group.save()

        assert osf_group.name == new_name

    def test_remove_group(self, manager, member, osf_group):
        osf_group_name = osf_group.name
        manager_group_name = osf_group.manager_group.name
        member_group_name = osf_group.member_group.name

        osf_group.remove_group(Auth(manager))
        assert not OSFGroup.objects.filter(name=osf_group_name).exists()
        assert not Group.objects.filter(name=manager_group_name).exists()
        assert not Group.objects.filter(name=member_group_name).exists()

        assert manager_group_name not in manager.groups.values_list('name', flat=True)

    def test_user_groups_property(self, manager, member, osf_group):
        assert osf_group in manager.osf_groups
        assert osf_group in member.osf_groups

        other_group = OSFGroupFactory()

        assert other_group not in manager.osf_groups
        assert other_group not in member.osf_groups

    def test_add_osf_group_to_node(self, manager, member, user_two, osf_group, project):
        # noncontributor
        with pytest.raises(PermissionsError):
            project.add_osf_group(osf_group, 'write', auth=Auth(member))

        # Non-admin on project
        project.add_contributor(user_two, 'write')
        project.save()
        with pytest.raises(PermissionsError):
            project.add_osf_group(osf_group, 'write', auth=Auth(user_two))

        project.add_osf_group(osf_group, 'read', auth=Auth(manager))
        # Manager was already a node admin
        assert project.has_permission(manager, 'admin') is True
        assert project.has_permission(manager, 'write') is True
        assert project.has_permission(manager, 'read') is True

        assert project.has_permission(member, 'admin') is False
        assert project.has_permission(member, 'write') is False
        assert project.has_permission(member, 'read') is True

        project.add_osf_group(osf_group, 'write', auth=Auth(manager))
        assert project.has_permission(member, 'admin') is False
        assert project.has_permission(member, 'write') is True
        assert project.has_permission(member, 'read') is True

        project.add_osf_group(osf_group, 'admin', auth=Auth(manager))
        assert project.has_permission(member, 'admin') is True
        assert project.has_permission(member, 'write') is True
        assert project.has_permission(member, 'read') is True

    def test_add_osf_group_to_node_default_permission(self, manager, member, osf_group, project):
        project.add_osf_group(osf_group, auth=Auth(manager))

        assert project.has_permission(manager, 'admin') is True
        assert project.has_permission(manager, 'write') is True
        assert project.has_permission(manager, 'read') is True

        # osf_group given write permissions by default
        assert project.has_permission(member, 'admin') is False
        assert project.has_permission(member, 'write') is True
        assert project.has_permission(member, 'read') is True

    def test_remove_osf_group_from_node(self, manager, member, user_two, osf_group, project):
        # noncontributor
        with pytest.raises(PermissionsError):
            project.remove_osf_group(osf_group, auth=Auth(member))

        project.add_osf_group(osf_group, 'admin', auth=Auth(manager))
        assert project.has_permission(member, 'admin') is True
        assert project.has_permission(member, 'write') is True
        assert project.has_permission(member, 'read') is True

        project.remove_osf_group(osf_group, auth=Auth(manager))
        assert project.has_permission(member, 'admin') is False
        assert project.has_permission(member, 'write') is False
        assert project.has_permission(member, 'read') is False

        # Project admin who does not belong to the manager group can remove the group
        project.add_osf_group(osf_group, 'admin', auth=Auth(manager))
        project.add_contributor(user_two, 'admin')
        project.save()
        project.remove_osf_group(osf_group, auth=Auth(user_two))
        assert project.has_permission(member, 'admin') is False
        assert project.has_permission(member, 'write') is False
        assert project.has_permission(member, 'read') is False

    def test_node_groups_property(self, manager, member, osf_group, project):
        project.add_osf_group(osf_group, 'admin', auth=Auth(manager))
        assert osf_group.member_group in project.osf_groups
        assert len(project.osf_groups) == 1

        group_two = OSFGroupFactory(creator=manager)
        project.add_osf_group(group_two, 'admin', auth=Auth(manager))
        assert group_two.member_group in project.osf_groups
        assert len(project.osf_groups) == 2

    def test_belongs_to_osfgroup_property(self, manager, member, user_two, osf_group):
        assert osf_group.belongs_to_osfgroup(manager) is True
        assert osf_group.belongs_to_osfgroup(member) is True
        assert osf_group.belongs_to_osfgroup(user_two) is False
