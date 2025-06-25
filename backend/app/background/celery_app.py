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
    # Beat schedule for periodic tasks
    beat_schedule={
        'cleanup-orphaned-data': {
            'task': 'app.background.tasks.cleanup_orphaned_data',
            'schedule': 86400.0,  # Run daily (24 hours)
        },
        'periodic-refresh-github-sources': {
            'task': 'app.background.tasks.periodic_refresh_all_github_sources',
            'schedule': 21600.0,  # Run every 6 hours
        },
    },
)

if __name__ == "__main__":
    celery_app.start()