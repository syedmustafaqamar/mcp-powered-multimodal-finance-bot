"""Celery configuration settings."""

from app.core.config import settings


class CeleryConfig:
    """Celery configuration class."""

    @property
    def broker_url(self) -> str:
        """Get Celery broker URL."""
        return settings.CELERY_BROKER_URL

    @property
    def result_backend(self) -> str:
        """Get Celery result backend URL."""
        return settings.CELERY_RESULT_BACKEND

    # Task serialization
    task_serializer: str = "json"
    accept_content: list = ["json"]
    result_serializer: str = "json"
    timezone: str = "UTC"
    enable_utc: bool = True

    # Task execution
    task_track_started: bool = True
    task_time_limit: int = 30 * 60  # 30 minutes
    task_soft_time_limit: int = 25 * 60  # 25 minutes
    worker_prefetch_multiplier: int = 4
    worker_max_tasks_per_child: int = 1000

    # Result backend settings
    result_expires: int = 3600  # 1 hour
    result_persistent: bool = True

    # Task routing (can be extended)
    task_routes: dict = {}

    # Task discovery
    task_always_eager: bool = False  # Set to True for testing (synchronous execution)
    task_eager_propagates: bool = True