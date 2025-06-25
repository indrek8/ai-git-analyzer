from celery import Celery
from app.config import settings

# Create Celery app
celery_app = Celery(
    "git_analyzer",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.background.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

if __name__ == "__main__":
    celery_app.start()