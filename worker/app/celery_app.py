import os

from celery import Celery

celery = Celery(
    "notebazar",
    broker=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
    backend=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
)

from . import tasks  # noqa: E402,F401
