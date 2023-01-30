from webmentions import db
from webmentions.db.models import FeedTask, Article
from webmentions.feed_queue import FeedQueue
from webmentions import queue_utils
from webmentions.scanner.feed import link_generator_from_feed, feed_from_url


def _process_feed(feed_task: FeedTask) -> None:
    # TODO(tech debt): move this to a package where it belongs, this is business logic, not queue
    #  logic
    print(f'Checking {feed_task.feed_url}, we checked it last on {feed_task.last_scan_completed}')

    # TODO(reliability): support etags here
    feed = feed_from_url(feed_task.feed_url)
    assert feed
    articles = list(link_generator_from_feed(feed))
    all_article_urls = [article.absolute_url for article in articles]
    # TODO(reliability): exclude articles that are older than feed.last_reported_update_time
    with db.db_session() as session:
        # exclude articles that we've seen before
        seen_articles = session.query(Article.url).filter(
            Article.url.in_(
                all_article_urls
            )
        ).all()
        seen_articles = set(a for a, in seen_articles)
        retain_articles = [
            article for article in articles
            if article.absolute_url not in seen_articles
        ]

        articles_orm = [Article(url=a.absolute_url, feed_guid=a.guid) for a in retain_articles]
        session.add_all(articles_orm)
        session.flush()
        article_ids = [article.id for article in articles_orm]

    # TODO(reliability): delete old articles?
    print(article_ids)


class InProcessQueue(queue_utils.InProcessQueue[FeedTask]):
    def __init__(self) -> None:
        super().__init__(_process_feed)
