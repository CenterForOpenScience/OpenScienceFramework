# -*- coding: utf-8 -*-
"""Asynchronous task queue module."""
from celery import Celery
from celery.utils.log import get_task_logger
from osf.utils.requests import requests_retry_session
from framework.postcommit_tasks.handlers import get_task_from_postcommit_queue, enqueue_postcommit_task

from raven import Client
from raven.contrib.celery import register_signal

from website.settings import SENTRY_DSN, VERSION, CeleryConfig, OSF_PIGEON_URL
from django.apps import apps

app = Celery()
app.config_from_object(CeleryConfig)

if SENTRY_DSN:
    client = Client(SENTRY_DSN, release=VERSION, tags={'App': 'celery'})
    register_signal(client)

if CeleryConfig.broker_use_ssl:
    app.setup_security()

@app.task
def error_handler(task_id, task_name):
    """logs detailed message about tasks that raise exceptions

    :param task_id: TaskID of the failed task
    :param task_name: name of task that failed
    """
    # get the current logger
    logger = get_task_logger(__name__)
    # query the broker for the AsyncResult
    result = app.AsyncResult(task_id)
    excep = result.get(propagate=False)
    # log detailed error mesage in error log
    logger.error('#####FAILURE LOG BEGIN#####\n'
                r'Task {0} raised exception: {0}\n\{0}\n'
                '#####FAILURE LOG STOP#####'.format(task_name, excep, result.traceback))


@app.task(max_retries=5, default_retry_delay=60, ignore_results=False)
def _archive_to_ia(node_id):
    requests_retry_session().post(f'{OSF_PIGEON_URL}archive/{node_id}')

def archive_to_ia(node):
    enqueue_postcommit_task(_archive_to_ia, (node._id,), {}, celery=True)

@app.task(max_retries=5, default_retry_delay=60, ignore_results=False)
def _update_ia_metadata(node_id, data):
    requests_retry_session().post(f'{OSF_PIGEON_URL}metadata/{node_id}', json=data).raise_for_status()

def update_ia_metadata(node, data=None):
    """
    This debounces/throttles requests by grabbing a pending task and overriding it instead of making a new one every
    pre-commit m2m change.

    IA wants us to brand our specific osf metadata with a `osf_` prefix. So we are following IA_MAPPED_NAMES.
    """
    Registration = apps.get_model('osf.registration')
    if not data:
        allowed_metadata = Registration.SYNCED_WITH_IA.intersection(node.get_dirty_fields().keys())
        data = {key: str(getattr(node, key)) for key in allowed_metadata}

    for key in data.keys():
        data[Registration.IA_MAPPED_NAMES.get(key, key)] = data.pop(key)

    if getattr(node, 'ia_url', None) and node.is_public:
        task = get_task_from_postcommit_queue(
            'framework.celery_tasks._update_ia_metadata',
            predicate=lambda task: task.args[0] == node._id and data.keys() == task.args[1].keys()
        )
        if task:
            task.args = (node._id, data, )
        else:
            enqueue_postcommit_task(_update_ia_metadata, (node._id, data, ), {}, celery=True)
