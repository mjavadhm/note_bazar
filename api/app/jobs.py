from celery import Celery

from .config import settings

celery_client = Celery("notebazar", broker=settings.redis_url)


def enqueue_preview(note_id: int) -> None:
    celery_client.send_task("notebazar.generate_preview", args=[note_id])
