from webmentions import db
from webmentions.db.models import Article, OutboundNotification
from webmentions.scanner import article_handler
from webmentions.scanner.mention_detector import fetch_page_check_mention_capabilities
from webmentions.util import aqueue
from webmentions import log

from typing import Optional

from webmentions.util.time import now

_log = log.get(__name__)


class InProcessArticleQueue(aqueue.InProcessQueue[str]):
    def __init__(self, notification_queue: aqueue.TaskQueue[str]) -> None:
        self.notification_queue = notification_queue

        super().__init__(self._process_item)

    def _process_item(self, article_id: str) -> None:
        _log.info(f"Processing {article_id}")
        with db.readonly_session() as session:
            article: Optional[Article] = session.query(Article).filter_by(
                id=article_id
            ).one_or_none()
            # expunge the article here so that the DB can close
            session.expunge(article)
        if not article:
            # Deleted or something idk
            _log.warning(f"Article {article_id} not found")
            return

        # NOTE: we're running everything in a single, sync handler here. If there's a slow server or
        # whatever, we're going to tank performance of processing the rest of the article. Currently
        # we're just fixing that with timeouts.
        # TODO(tech debt): add test that this resolves to an absolute URL within the HTML but doesn't
        # emit redirected URLs via HTTP30whatevers
        links = article_handler.parse_page_find_links(article.url)
        pending_notifications = []
        for link in links:
            capabilities = fetch_page_check_mention_capabilities(link)
            if capabilities:
                notif = OutboundNotification(
                    source_article_id=article_id,
                    target_url=link,
                    webmention_endpoint=capabilities.webmention_url,
                    pingback_endpoint=capabilities.pingback_url,
                )
                pending_notifications.append(notif)

        with db.db_session() as session:
            article = session.merge(article)
            article.page_scan_completed_at = now()

            session.add_all(pending_notifications)
            session.flush()
            notification_ids = [pn.id for pn in pending_notifications]

        # TODO: emit notification IDs to queue
        for notification_id in notification_ids:
            self.notification_queue.enqueue(notification_id)
