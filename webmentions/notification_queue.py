from typing import Optional

from sqlalchemy.orm import joinedload

from webmentions import db, log
from webmentions.db.models import OutboundNotification, STATE_PROCESSING
from webmentions.scanner.mention_detector import MentionCapabilities
from webmentions.util import aqueue
from webmentions.scanner import mention_sender


_log = log.get(__name__)


def _status_terminal(notification: OutboundNotification) -> bool:
    return notification.state != STATE_PROCESSING


def _process_item(notification_id: str) -> None:
    _log.info(f"Starting {notification_id}")
    with db.readonly_session() as session:
        notification: Optional[OutboundNotification] = (
            session.query(OutboundNotification)
            .options(joinedload(OutboundNotification.source_article))
            .filter_by(id=notification_id).one_or_none())
        session.expunge_all()

    if not notification:
        _log.warning(f"Skipping {notification_id}, it has vanished")
        return

    if _status_terminal(notification):
        # Nothing to do
        _log.warning(f"Skipping {notification_id}, already processed")
        return

    mc = mention_sender.MentionCandidate(
        mentioner_url=notification.source_article.url,
        mentioned_url=notification.target_url,
        capabilities=MentionCapabilities(
            webmention_url=notification.webmention_endpoint,
            pingback_url=notification.pingback_endpoint
        ),
    )

    mention_sender.send_mention(mc)


class InProcessNotificationQueue(aqueue.InProcessQueue[str]):
    def __init__(self) -> None:
        super().__init__(item_processor=_process_item)
