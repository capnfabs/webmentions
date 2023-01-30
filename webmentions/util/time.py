import datetime


def now() -> datetime.datetime:
    return datetime.datetime.utcnow()


HOUR = datetime.timedelta(hours=1)
DAY = datetime.timedelta(days=1)
