"""
Scripts for attempted recovery of corrupted git repos. Note: because some
meta-data is not preserved, the recovered SHAs are different from the
originals; after recovery, the SHAs stored in the database will be different.
Original SHAs are stored in NodeFile::backup.
"""

import os
import shutil
import logging
import subprocess

from website import settings
from website.app import init_app
from website.addons.osffiles.model import NodeFile

app = init_app('website.settings', set_backends=True, routes=True)


RECOVER_PATH = '/home/jmcarp/git-recovery'


def get_node_path(node):
    return os.path.join(settings.UPLOADS_PATH, node._id)


def get_backup_path(node):
    return os.path.join(RECOVER_PATH, node._id)


def collect_commits(node):
    
    commits = []

    for name, versions in node.files_versions.iteritems():
        for version in versions:
            node_file = NodeFile.load(version)
            if not node_file:
                continue
            commits.append(node_file)

    return sorted(commits, key=lambda commit: commit.date_uploaded)


def restore_from_commit(commit, old_path, new_path):
    
    out_name = os.path.join(new_path, commit.filename)
    with open(out_name, 'w') as fp:
        subprocess.call(
            ['git', 'show', '{0}:{1}'.format(commit.git_commit, commit.filename)],
            cwd=old_path,
            stdout=fp,
        )


def get_current_hash(path):
    return subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'],
        cwd=path,

    ).strip()


def get_committers(commit, path):
    
    output = subprocess.check_output(
        [
            'git', 'show', 
            commit.git_commit,
            '--pretty=format:%cn:%ce|%an:%ae',
        ],
        cwd=path,
    )
    return [
        part.split(':')
        for part in output.split('\n')[0].split('|')
    ]


def apply_commit(commit, old_path, new_path):
    
    subprocess.call(
        ['git', 'add', commit.filename],
        cwd=new_path,
    )

    committer, author = get_committers(commit, old_path)
    msg = '{0} updated'.format(commit.filename)

    subprocess.call(
        [
            'git', 'commit', 
            '-m', msg,
            '--date', commit.date_uploaded.isoformat(),
            '--author', '{0} <{1}>'.format(*author),
        ],
        cwd=new_path,
    )

    # Amend committer info
    subprocess.call(
        ['git', 'config', 'user.name', committer[0]],
        cwd=new_path,
    )
    subprocess.call(
        ['git', 'config', 'user.email', committer[1]],
        cwd=new_path,
    )
    subprocess.call(
        ['git', 'commit', '--amend', '-m', msg],
        cwd=new_path,
    )

    sha = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'],
        cwd=new_path,
    ).strip()
    commit.backup['git_commit'], commit.git_commit = commit.git_commit, sha
    logging.warn('Setting SHA to {0} on file {1}'.format(sha, commit.filename))
    commit.save()


def mkdir_safe(path):

    try:
        os.makedirs(path)
    except OSError:
        pass


def restore_repo(node):

    node_path = get_node_path(node)
    backup_path = get_backup_path(node)

    shutil.move(node_path, RECOVER_PATH)

    mkdir_safe(node_path)

    subprocess.call(
        ['git', 'init'],
        cwd=node_path,
    )

    commits = collect_commits(node)

    for commit in commits:
        try:
            restore_from_commit(commit, backup_path, node_path)
            apply_commit(commit, backup_path, node_path)
        except subprocess.CalledProcessError as error:
            logging.exception(error)
            continue
