from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db

router = APIRouter()

@router.get("/")
async def get_repositories(db: Session = Depends(get_db)):
    # TODO: Implement repository listing
    return {"repositories": []}

@router.post("/")
async def add_repository(repo_url: str, provider: str = "github", db: Session = Depends(get_db)):
    # TODO: Implement repository addition
    return {"message": f"Repository {repo_url} added successfully", "provider": provider}

@router.delete("/{repo_id}")
async def remove_repository(repo_id: int, db: Session = Depends(get_db)):
    # TODO: Implement repository removal
    return {"message": f"Repository {repo_id} removed successfully"}

@router.post("/{repo_id}/sync")
async def sync_repository(repo_id: int, db: Session = Depends(get_db)):
    # TODO: Trigger background sync job
    return {"message": f"Sync started for repository {repo_id}"}