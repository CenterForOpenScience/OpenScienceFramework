import os
import json
import logging
import sys

from modularodm import Q, storage
from modularodm.exceptions import NoResultsFound

from framework.mongo import set_up_storage
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils
from website import settings
from website.project.taxonomies import Subject


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def update_taxonomies(filename, dry_run=True):
    # Flat taxonomy is stored locally, read in here
    with open(
        os.path.join(
            settings.APP_PATH,
            'website', 'static', filename
        )
    ) as fp:
        taxonomy = json.load(fp)

        for subject_path in taxonomy.get('data'):
            subjects = subject_path.split('_')
            text = subjects[-1]

            # Search for parent subject, get id if it exists
            parent = None
            if len(subjects) > 1:
                try:
                    parent = Subject.find_one(Q('text', 'eq', subjects[-2]))
                except NoResultsFound:
                    pass

            try:
                subject = Subject.find_one(Q('text', 'eq', text))
            except (NoResultsFound):    
                # If subject does not yet exist, create it
                subject = Subject(
                    text=text,
                    parents=[parent] if parent else [],
                )
                logger.info(u'Creating Subject "{}":{}{}'.format(
                    subject.text,
                    subject._id,
                    u' with parent {}:{}'.format(parent.text, parent._id) if parent else ''
                ))
            else:
                # If subject does exist, append parent_id if not already added
                subject.text = text
                if parent not in subject.parents:
                    subject.parents.append(parent)
                    logger.info(u'Adding parent "{}":{} to Subject "{}":{}'.format(
                        parent.text, parent._id,
                        subject.text, subject._id
                    ))

            subject.save()

    if dry_run:
        raise RuntimeError('Dry run, transaction rolled back')

def main():
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    set_up_storage([Subject], storage.MongoStorage)    
    with TokuTransaction():
        update_taxonomies('plos_taxonomy.json', dry_run=dry_run)
        update_taxonomies('other_taxonomy.json', dry_run=dry_run)

if __name__ == '__main__':
    main()
