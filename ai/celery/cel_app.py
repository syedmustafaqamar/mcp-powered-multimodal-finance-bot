from celery import Celery

from ai.celery.cel_config import CeleryConfig
from ai.config import settings


celery_app = Celery(
    "finance_ai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.config_from_object(CeleryConfig)
celery_app.conf.imports = (
    "ai.celery.tasks.ingestion",
    "ai.celery.tasks.rag",
)
