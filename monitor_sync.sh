#\!/bin/bash
while true; do
  echo "=== $(date) ==="
  docker-compose exec backend python -c "
from app.database import get_db
from app.models.repository import Repository
db = next(get_db())
repos = db.query(Repository).all()
status_counts = {}
for repo in repos:
    status = repo.sync_status
    status_counts[status] = status_counts.get(status, 0) + 1
print(f'Status: {status_counts}')
  "
  sleep 30
done
