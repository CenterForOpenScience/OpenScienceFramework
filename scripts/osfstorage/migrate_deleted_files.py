import logging
from modularodm import Q
from website.app import init_app
from website.addons.osfstorage.model import OsfStorageFileNode
from scripts import utils as scripts_utils


logger = logging.getLogger(__name__)


def main():
    for file in OsfStorageFileNode.find(Q('is_deleted', 'eq', True)):
        file.delete()
        logger.info(u'Moving {!r} to the trashed collections'.format(file))


if __name__ == '__main__':
    scripts_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    main()
