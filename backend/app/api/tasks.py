from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from celery.result import AsyncResult

from app.database import get_db
from app.models.user import User
from app.models.repository import Repository
from app.models.github_user import GitHubUser
from app.models.github_organization import GitHubOrganization
from app.api.auth import get_current_user
from app.background.tasks import (
    bulk_sync_repositories,
    refresh_github_user_repositories,
    refresh_github_organization_repositories,
    periodic_refresh_all_github_sources,
    sync_repository
)

router = APIRouter()

# Pydantic models
class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: Optional[int] = None
    result: Optional[dict] = None
    meta: Optional[dict] = None

class BulkSyncRequest(BaseModel):
    repository_ids: List[int]

class TaskListResponse(BaseModel):
    task_id: str
    task_name: str
    status: str
    created_at: Optional[str] = None
    progress: Optional[int] = None

@router.post("/repositories/bulk-sync")
async def start_bulk_repository_sync(
    request: BulkSyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start bulk synchronization of multiple repositories"""
    
    # Validate repositories belong to user
    repositories = db.query(Repository).filter(
        Repository.id.in_(request.repository_ids),
        Repository.owner_id == current_user.id
    ).all()
    
    if len(repositories) != len(request.repository_ids):
        raise HTTPException(status_code=400, detail="Some repositories not found or not owned by user")
    
    # Start bulk sync task
    task = bulk_sync_repositories.delay(request.repository_ids, current_user.id)
    
    return {
        "task_id": task.id,
        "status": "started",
        "message": f"Bulk sync started for {len(request.repository_ids)} repositories"
    }

@router.post("/github-users/{user_id}/refresh")
async def refresh_github_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Refresh repository list for a GitHub user"""
    
    github_user = db.query(GitHubUser).filter(
        GitHubUser.id == user_id,
        GitHubUser.added_by_user_id == current_user.id
    ).first()
    
    if not github_user:
        raise HTTPException(status_code=404, detail="GitHub user not found")
    
    # Start refresh task
    task = refresh_github_user_repositories.delay(user_id)
    
    return {
        "task_id": task.id,
        "status": "started",
        "message": f"Repository refresh started for GitHub user {github_user.username}"
    }

@router.post("/github-organizations/{org_id}/refresh")
async def refresh_github_organization(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Refresh repository list for a GitHub organization"""
    
    github_org = db.query(GitHubOrganization).filter(
        GitHubOrganization.id == org_id,
        GitHubOrganization.added_by_user_id == current_user.id
    ).first()
    
    if not github_org:
        raise HTTPException(status_code=404, detail="GitHub organization not found")
    
    # Start refresh task
    task = refresh_github_organization_repositories.delay(org_id)
    
    return {
        "task_id": task.id,
        "status": "started",
        "message": f"Repository refresh started for GitHub organization {github_org.login}"
    }

@router.post("/periodic-refresh")
async def start_periodic_refresh(
    current_user: User = Depends(get_current_user)
):
    """Start periodic refresh of all GitHub sources (admin only)"""
    
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Start periodic refresh task
    task = periodic_refresh_all_github_sources.delay()
    
    return {
        "task_id": task.id,
        "status": "started",
        "message": "Periodic refresh started for all GitHub sources"
    }

@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get status of a background task"""
    
    try:
        result = AsyncResult(task_id)
        
        response = {
            "task_id": task_id,
            "status": result.status.lower(),
        }
        
        if result.status == 'PROGRESS':
            response["meta"] = result.info
            response["progress"] = result.info.get('progress', 0)
        elif result.status == 'SUCCESS':
            response["result"] = result.result
            response["progress"] = 100
        elif result.status == 'FAILURE':
            response["result"] = {"error": str(result.info)}
            response["progress"] = 0
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid task ID: {str(e)}")

@router.delete("/cancel/{task_id}")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Cancel a running background task"""
    
    try:
        result = AsyncResult(task_id)
        
        if result.status in ['PENDING', 'PROGRESS']:
            result.revoke(terminate=True)
            return {"message": f"Task {task_id} cancelled successfully"}
        else:
            return {"message": f"Task {task_id} cannot be cancelled (status: {result.status})"}
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to cancel task: {str(e)}")

@router.get("/repository/{repo_id}/sync-status")
async def get_repository_sync_status(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed sync status for a specific repository"""
    
    repository = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.owner_id == current_user.id
    ).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    return {
        "repository_id": repository.id,
        "name": repository.name,
        "sync_status": repository.sync_status,
        "last_synced_at": repository.last_synced_at,
        "sync_error": repository.sync_error
    }

@router.post("/repository/{repo_id}/force-sync")
async def force_repository_sync(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Force immediate sync of a specific repository"""
    
    repository = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.owner_id == current_user.id
    ).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Reset any previous sync status
    repository.sync_status = "pending"
    repository.sync_error = None
    db.commit()
    
    # Start sync task
    task = sync_repository.delay(repo_id)
    
    return {
        "task_id": task.id,
        "status": "started",
        "message": f"Force sync started for repository {repository.name}"
    }

@router.get("/active")
async def get_active_tasks(
    current_user: User = Depends(get_current_user)
):
    """Get list of active tasks for the current user"""
    
    # This would require additional setup to track user tasks
    # For now, return a placeholder response
    return {
        "active_tasks": [],
        "message": "Task tracking requires additional setup"
    }

@router.get("/stats")
async def get_task_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get task execution statistics"""
    
    # Get repository sync statistics
    total_repos = db.query(Repository).filter(Repository.owner_id == current_user.id).count()
    synced_repos = db.query(Repository).filter(
        Repository.owner_id == current_user.id,
        Repository.sync_status == "completed"
    ).count()
    failed_repos = db.query(Repository).filter(
        Repository.owner_id == current_user.id,
        Repository.sync_status == "failed"
    ).count()
    pending_repos = db.query(Repository).filter(
        Repository.owner_id == current_user.id,
        Repository.sync_status.in_(["pending", "syncing"])
    ).count()
    
    # Get GitHub source statistics
    github_users = db.query(GitHubUser).filter(GitHubUser.added_by_user_id == current_user.id).count()
    github_orgs = db.query(GitHubOrganization).filter(GitHubOrganization.added_by_user_id == current_user.id).count()
    
    return {
        "repository_sync": {
            "total": total_repos,
            "completed": synced_repos,
            "failed": failed_repos,
            "pending": pending_repos
        },
        "github_sources": {
            "users": github_users,
            "organizations": github_orgs
        }
    }