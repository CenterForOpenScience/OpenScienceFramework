import celery

from framework.celery_tasks import handlers

from website.archiver import utils as archiver_utils
from website.archiver import (
    ARCHIVER_UNCAUGHT_ERROR,
)
from website.archiver import signals as archiver_signals

from website.project import signals as project_signals
from osf_pigeon.pigeon import main as IA_archiver
from framework.celery_tasks import app as celery_app

from website import settings

@project_signals.after_create_registration.connect
def after_register(src, dst, user):
    """Blinker listener for registration initiations. Enqueqes a chain
    of archive tasks for the current node and its descendants

    :param src: Node being registered
    :param dst: registration Node
    :param user: registration initiator
    """
    # Prevent circular import with app.py
    from website.archiver import tasks
    archiver_utils.before_archive(dst, user)
    if dst.root != dst:  # if not top-level registration
        return
    archive_tasks = [tasks.archive(job_pk=t.archive_job._id) for t in dst.node_and_primary_descendants()]
    handlers.enqueue_task(
        celery.chain(archive_tasks)
    )


@project_signals.archive_callback.connect
def archive_callback(dst):
    """Blinker listener for updates to the archive task. When the tree of ArchiveJob
    instances is complete, proceed to send success or failure mails

    :param dst: registration Node
    """
    root = dst.root
    root_job = root.archive_job
    if not root_job.archive_tree_finished():
        return
    if root_job.sent:
        return
    if root_job.success:
        # Prevent circular import with app.py
        from website.archiver import tasks
        tasks.archive_success.delay(dst_pk=root._id, job_pk=root_job._id)
    else:
        archiver_utils.handle_archive_fail(
            ARCHIVER_UNCAUGHT_ERROR,
            root.registered_from,
            root,
            root.registered_user,
            dst.archive_job.target_addons.all(),
        )


@archiver_signals.archive_fail.connect
def archive_fail(dst, errors):
    reason = dst.archive_status
    root_job = dst.root.archive_job
    if root_job.sent:
        return
    root_job.sent = True
    root_job.save()
    archiver_utils.handle_archive_fail(
        reason,
        dst.root.registered_from,
        dst.root,
        dst.root.registered_user,
        errors
    )


@project_signals.after_registration_or_embargo_lifted.connect
def after_registration_or_embargo_lifted(registration):
    from osf.models import Registration

    if settings.IA_ARCHIVE_ENABLED:
        children = list(Registration.objects.get_children(registration, include_root=True))
        for registration in children:
            run_IA_archiver.delay(registration._id)


@celery_app.task(name='website.archiver.listeners.run_IA_archiver', ignore_results=True)
def run_IA_archiver(registration_guid):
    from osf.models import Registration
    registration = Registration.load(registration_guid)
    registration.IA_url = IA_archiver(
        registration._id,
        datacite_password=settings.DATACITE_PASSWORD,
        datacite_username=settings.DATACITE_USERNAME,
        ia_access_key=settings.IA_ACCESS_KEY,
        ia_secret_key=settings.IA_SECRET_KEY,
        osf_files_url=settings.WATERBUTLER_URL + '/',
        osf_api_url=settings.API_DOMAIN,
        collection_name=settings.IA_ROOT_COLLECTION,
        id_version=settings.IA_ID_VERSION,
        datacite_url=settings.DATACITE_URL
    )
    registration.save()