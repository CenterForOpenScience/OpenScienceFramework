from framework.logging import logger
from framework.celery_tasks import app as celery_app
from framework.mongo import get_cache_key as get_request

from website import settings
from website.util import akismet, get_headers_from_request

NODE_SPAM_FIELDS = set((
    'title',
    'description',
    'wiki_pages_current',
    'node_license'
))

def _get_client():
    return akismet.AkismetClient(
        apikey=settings.AKISMET_APIKEY,
        website=settings.DOMAIN,
        verify=True
    )

def _get_content(node):
    from website.addons.wiki.model import NodeWikiPage
    content = []
    for field in NODE_SPAM_FIELDS:
        if 'wiki' in field:
            content.append('\n'.join([
                NodeWikiPage.load(x).raw_text(node)
                for x in node.wiki_pages_current.values()
            ]))
            continue
        content.append((getattr(node, field, None) or '').encode('utf-8'))
    return '\n'.join(content)


@celery_app.task(ignore_result=True)
def confirm_spam(node_id):
    from website.models import Node
    node = Node.load(node_id)
    request_headers = get_headers_from_request(
        get_request()
    )
    client = _get_client()
    content = _get_content(node)
    client.submit_spam(
        user_ip=request_headers['Remote-Addr'],
        user_agent=request_headers['User-Agent'],
        referrer=request_headers.get('Referrer'),
        comment_content=content,
        comment_author=node.creator.fullname,
        # comment_author_email=node.creator.username,
    )

@celery_app.task(ignore_result=True)
def confirm_ham(node_id):
    from website.models import Node
    node = Node.load(node_id)
    request_headers = get_headers_from_request(
        get_request()
    )
    content = _get_content(node)
    client = _get_client()
    client.submit_ham(
        user_ip=request_headers['Remote-Addr'],
        user_agent=request_headers['User-Agent'],
        referrer=request_headers.get('Referrer'),
        comment_content=content,
        comment_author=node.creator.fullname,
        # comment_author_email=node.creator.username,
    )

def _check_for_spam(node, content, request_headers):
    client = _get_client()

    is_possible_spam, pro_tip = client.check_comment(
        user_ip=request_headers['Remote-Addr'],
        user_agent=request_headers['User-Agent'],
        referrer=request_headers.get('Referrer'),
        comment_content=content,
        comment_author=node.creator.fullname,
        # comment_author_email=node.creator.username,
    )

    if is_possible_spam:
        logger.info("Node '{}' ({}) smells like SPAM".format(
            node.title.encode('utf-8'),
            node._id
        ))
        node.flag_spam(save=True)
        return True
    else:
        logger.info("Node '{}' ({}) smells like HAM".format(
            node.title.encode('utf-8'),
            node._id
        ))
        return False

def check_node_for_spam(node, request_headers):
    content = _get_content(node)
    return _check_for_spam(node, content, request_headers)
