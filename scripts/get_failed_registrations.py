# -*- coding: utf-8 -*-
import sys
import logging

from datetime import datetime
from framework.celery_tasks import app as celery_app
from framework.transactions.context import TokuTransaction
from modularodm import Q

from website.app import init_app
from website.archiver import ARCHIVER_INITIATED
from website.archiver.model import ArchiveJob
from website import mails
from website.settings import ARCHIVE_TIMEOUT_TIMEDELTA, SUPPORT_EMAIL

from scripts import utils as script_utils


logger = logging.getLogger(__name__)
expired_if_before = datetime.utcnow() - ARCHIVE_TIMEOUT_TIMEDELTA


def find_failed_registrations():
    jobs = ArchiveJob.find(
        Q('sent', 'eq', False) &
        Q('datetime_initiated', 'lt', expired_if_before) &
        Q('status', 'eq', ARCHIVER_INITIATED)
    )
    return {node.root for node in [job.dst_node for job in jobs] if node}


def report_failed_registrations(dry_run):
    init_app(set_backends=True, routes=False)
    count = 0
    failed = find_failed_registrations()
    if not dry_run:
        yesterday = expired_if_before.strftime('%Y-%m-%d')
        if failed:
            message = ''
            for f in failed:
                if not f.registered_from:
                    fail_message = 'Node {0} with title {} and creator {} had registered_from == None.'\
                        .format(f._id, f.title, f.creator._id)
                    logging.info(fail_message)
                    message += fail_message + '\n'
                    count += 1
                    continue
                if not f.archive_job:  # Be extra sure not to delete legacy registrations
                    continue
                fail_message = 'Node {0} with title {} and creator {} is a failed registration from Node {}'\
                    .format(f._id, f.title, f.creator._id, f.registered_from_id)
                logging.info(fail_message)
                message += fail_message + '\n'
                count += 1
            total = 'Total: {} failed registrations on {}'.format(count, yesterday)
            logging.info(total)
            message += total
            mails.send_mail(
                to_addr=SUPPORT_EMAIL,
                mail=mails.EMPTY,
                subject='Failed registration on {}'.format(yesterday),
                message=message
            )
        else:
            mails.send_mail(
                to_addr=SUPPORT_EMAIL,
                mail=mails.EMPTY,
                subject='None failed registration on {}'.format(yesterday),
                message='There are no failed registration on {}'.format(
                    yesterday
                )
            )


@celery_app.task(name='scripts.get_failed_registrations')
def run_main(dry_run=True):
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        report_failed_registrations(dry_run=dry)
