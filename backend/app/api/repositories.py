from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.repository import Repository, RepositoryProvider
from app.api.auth import get_current_user
from app.background.tasks import sync_repository

router = APIRouter()

class RepositoryCreate(BaseModel):
    repo_url: str
    provider: str = "github"

class RepositoryResponse(BaseModel):
    id: int
    name: str
    full_name: str
    url: str
    provider: str
    sync_status: str
    is_active: bool
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[RepositoryResponse])
async def get_repositories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repositories = db.query(Repository).filter(Repository.owner_id == current_user.id).all()
    return repositories

@router.post("/", response_model=RepositoryResponse)
async def add_repository(
    repo_data: RepositoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Parse repository URL to extract name and full_name
    repo_url = repo_data.repo_url.rstrip('/')
    if repo_url.endswith('.git'):
        repo_url = repo_url[:-4]
    
    # Extract repository name from URL
    parts = repo_url.split('/')
    if len(parts) >= 2:
        full_name = f"{parts[-2]}/{parts[-1]}"
        name = parts[-1]
    else:
        raise HTTPException(status_code=400, detail="Invalid repository URL format")
    
    # Check if repository already exists for this user
    existing_repo = db.query(Repository).filter(
        Repository.url == repo_url,
        Repository.owner_id == current_user.id
    ).first()
    
    if existing_repo:
        raise HTTPException(status_code=400, detail="Repository already exists")
    
    # Create new repository
    repository = Repository(
        name=name,
        full_name=full_name,
        url=repo_url,
        provider=RepositoryProvider(repo_data.provider),
        owner_id=current_user.id,
        sync_status="pending"
    )
    
    db.add(repository)
    db.commit()
    db.refresh(repository)
    
    # Trigger background sync
    sync_repository.delay(repository.id)
    
    return repository

@router.delete("/{repo_id}")
async def remove_repository(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repository = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.owner_id == current_user.id
    ).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    db.delete(repository)
    db.commit()
    return {"message": f"Repository {repository.name} removed successfully"}

@router.post("/{repo_id}/sync")
async def trigger_repository_sync(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repository = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.owner_id == current_user.id
    ).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Update status and trigger sync
    repository.sync_status = "pending"
    db.commit()
    
    # Trigger background sync
    sync_repository.delay(repository.id)
    
    return {"message": f"Sync started for repository {repository.name}"}