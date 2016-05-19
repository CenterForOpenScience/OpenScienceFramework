import logging
import sys

from modularodm import Q

from framework.transactions.context import TokuTransaction
from website.app import init_app
from website.models import NodeLog
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

def get_targets():
    return NodeLog.find(Q('action', 'eq', NodeLog.WIKI_DELETED))

def migrate(targets, dry_run=True):
    # iterate over targets
    logs = targets
    nodes = set()
    for log in logs:
        nodes.add(log.node)
    for node in nodes:
        versions = node.wiki_pages_versions
        current = node.wiki_pages_current
        updated_versions = {}
        for wiki in node.wiki_pages_versions:
            if wiki in current:
                updated_versions[wiki] = versions[wiki]
        if not dry_run:
            node.wiki_pages_versions = updated_versions
            node.save()

    if dry_run:
        raise RuntimeError('Dry run, transaction rolled back.')


def main():
    dry_run = False
    if '--dry' in sys.argv:
        dry_run = True
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate(targets=get_targets(), dry_run=dry_run)

if __name__ == "__main__":
    main()
