"""File: usage_audit.py
Find all users and projects where their total usage (current file + deleted files) is >= the set limit
Projects or users can have their GUID whitelisted via `usage_audit whitelist [GUID ...]`
User usage is defined as the total usage of all projects they have > READ access on
Project usage is defined as the total usage of it and all its children
total usage is defined as the sum of the size of all verions associated with X via OsfStorageFileNode and OsfStorageTrashedFileNode
"""
import os
import sys
import json
import logging
from collections import defaultdict

from modularodm import Q
from website import mails
from website.app import init_app
from website.project.model import Node
from website.addons.osfstorage import model

from scripts import utils as scripts_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

GBs = 1024 ** 3.0

USER_LIMIT = 5 * GBs
PROJECT_LIMIT = 5 * GBs

WHITE_LIST_PATH = os.path.join(os.path.dirname(__file__), 'usage_whitelist.json')


try:
    with open(WHITE_LIST_PATH, 'r') as fobj:
        WHITE_LIST = set(json.load(fobj))  # Cast to set for constant time look ups
    logger.info('Loaded whitelist.json from {}'.format(WHITE_LIST_PATH))
except IOError:
    WHITE_LIST = set()
    logger.warning('No whitelist found')


def add_to_white_list(gtg):
    gtg = set(gtg).difference(WHITE_LIST)
    logger.info('Adding {} to whitelist'.format(gtg))
    with open(WHITE_LIST_PATH, 'w') as fobj:
        json.dump(list(WHITE_LIST.union(gtg)), fobj)  # Sets are not JSON serializable
    logger.info('Whitelist updated to {}'.format(WHITE_LIST))


def get_usage(node):
    addon = node.get_addon('osfstorage')
    calculate_usage = lambda m: sum([v.size or 0 for fn in m.find(Q('node_settings', 'eq', addon)) for v in fn.versions])  # Sum all versions of all files of this node
    usage = (calculate_usage(model.OsfStorageFileNode), calculate_usage(model.OsfStorageTrashedFileNode))  # Sum both deleted and not deleted files, keep as a tuple (files, deletedfiles)
    return map(sum, zip(*([usage] + [get_usage(child) for child in node.nodes])))  # Adds tuples together, map(sum, zip((a, b), (c, d))) -> (a+c, b+d)


def main(send_email=False):
    logger.info('Starting Project storage audit')
    init_app(set_backends=True, routes=False)

    lines = []
    projects = {}
    users = defaultdict(lambda: (0, 0))

    for node in Node.find(Q('__backrefs.parent.node.nodes', 'eq', None)):  # ODM hack to ignore all nodes with parents
        if node._id in WHITE_LIST:
            continue  # Dont count whitelisted nodes against users
        projects[node] = get_usage(node)
        for contrib in node.contributors:
            if node.can_edit(user=contrib):
                users[contrib] = tuple(map(sum, zip(users[contrib], projects[node])))  # Adds tuples together, map(sum, zip((a, b), (c, d))) -> (a+c, b+d)

    filter_factory = lambda x: lambda (i, (u, d)): i._id not in WHITE_LIST and (u + d) >= x  # Returns a lambda that returns if i is in the whitelist and its storage usage is >= x

    for collection, limit in ((users, USER_LIMIT), (projects, PROJECT_LIMIT)):
        for item, (used, deleted) in filter(filter_factory(limit), collection.items()):
            line = '{!r} has exceeded the limit {:.2f}GBs ({}b) with {:.2f}GBs ({}b) used and {:.2f}GBs ({}b) deleted.'.format(item, limit / GBs, limit, used / GBs, used, deleted / GBs, deleted)
            logger.info(line)
            lines.append(line)

    if lines:
        if send_email:
            logger.info('Sending email...'.format(len(lines)))
            mails.send_mail('support@osf.io', mails.EMPTY, body='\n'.join(lines), subject='Script: OsfStorage usage audit')
        else:
            logger.info('send_email is False, not sending email'.format(len(lines)))
        logger.info('{} offending projects and users found'.format(len(lines)))
    else:
        logger.info('No offending projects or users found')


if __name__ == '__main__':
    scripts_utils.add_file_logger(logger, __file__)
    if len(sys.argv) > 1 and sys.argv[1] == 'whitelist':
        add_to_white_list(sys.argv[2:])
    else:
        main(send_email='send_mail' in sys.argv)
