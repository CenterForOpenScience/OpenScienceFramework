from website.files.models.base import File, Folder
from website.files.models.ext import PathFollowingFileNode


__all__ = ('GoogleDriveFile', 'GoogleDriveFolder', 'GoogleDriveFileNode')


class GoogleDriveFileNode(PathFollowingFileNode):
    provider = 'googledrive'


class GoogleDriveFolder(GoogleDriveFileNode, Folder):
    pass


class GoogleDriveFile(GoogleDriveFileNode, File):
    pass
