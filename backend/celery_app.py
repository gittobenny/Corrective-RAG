# Celery application used by PDF ingestion workers.

from celery import Celery

from backend.config import get_settings


settings = get_settings()
celery_app = Celery(
    "document_retriever",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["backend.tasks.document_tasks"],
)
celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    task_time_limit=900,
    task_soft_time_limit=840,
)
