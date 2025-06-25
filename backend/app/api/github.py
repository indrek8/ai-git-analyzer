from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List, Optional
from pydantic import BaseModel
import httpx
import secrets
import logging
from urllib.parse import urlencode

from app.database import get_db
from app.models.user import User
from app.models.github_user import GitHubUser
from app.models.github_organization import GitHubOrganization
from app.models.repository_selection import RepositorySelection, SelectionStatus
from app.api.auth import get_current_user
from app.config import settings
from app.repositories.github import GitHubClient

router = APIRouter()
logger = logging.getLogger(__name__)

# Import background tasks at module level to avoid import issues
try:
    from app.background.tasks import cleanup_deselected_repositories, cleanup_orphaned_data
except ImportError as e:
    logger.warning(f"Could not import background tasks: {e}")

# Pydantic models for request/response
class GitHubUserResponse(BaseModel):
    id: int
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    public_repos: int
    is_active: bool
    last_synced_at: Optional[str]
    
    class Config:
        from_attributes = True

class GitHubOrgResponse(BaseModel):
    id: int
    login: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    public_repos: int
    is_active: bool
    last_synced_at: Optional[str]
    
    class Config:
        from_attributes = True

class AddGitHubUserRequest(BaseModel):
    username: str

class RepositorySelectionResponse(BaseModel):
    id: int
    name: str
    full_name: str
    description: Optional[str]
    language: Optional[str]
    stargazers_count: int
    status: str
    is_private: bool
    is_fork: bool
    
    class Config:
        from_attributes = True

@router.get("/oauth/authorize")
async def github_oauth_authorize():
    """Initiate GitHub OAuth flow"""
    if not settings.github_client_id:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
    
    # Generate state parameter for security
    state = secrets.token_urlsafe(32)
    
    params = {
        'client_id': settings.github_client_id,
        'redirect_uri': settings.github_oauth_redirect_uri,
        'scope': settings.github_oauth_scopes,
        'state': state,
        'allow_signup': 'false'  # Only allow existing GitHub users
    }
    
    github_auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    
    return {
        "auth_url": github_auth_url,
        "state": state  # Frontend should store this to verify the callback
    }

@router.get("/oauth/callback")
async def github_oauth_callback(
    code: str,
    state: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Handle GitHub OAuth callback"""
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
    
    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_oauth_redirect_uri,
                "state": state
            }
        )
        
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code for token")
        
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")
    
    # Get user info with the access token
    github_client = GitHubClient(access_token)
    
    async with httpx.AsyncClient() as client:
        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        
        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch user info")
        
        user_data = user_response.json()
    
    return {
        "access_token": access_token,
        "user": user_data,
        "scopes": token_data.get("scope", "").split(",")
    }

@router.get("/users", response_model=List[GitHubUserResponse])
async def get_github_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all GitHub users being monitored by the current user"""
    github_users = db.query(GitHubUser).filter(
        GitHubUser.added_by_user_id == current_user.id
    ).all()
    return github_users

@router.post("/users", response_model=GitHubUserResponse)
async def add_github_user(
    user_data: AddGitHubUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a GitHub user for monitoring"""
    github_client = GitHubClient(current_user.github_token)
    
    try:
        # Fetch user info from GitHub API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/users/{user_data.username}",
                headers=github_client.headers
            )
            
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="GitHub user not found")
            
            if response.status_code == 403:
                raise HTTPException(
                    status_code=400, 
                    detail="GitHub API rate limit exceeded. Please configure a GitHub token in Settings."
                )
            
            response.raise_for_status()
            user_info = response.json()
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="GitHub user not found")
        elif e.response.status_code == 403:
            raise HTTPException(
                status_code=400, 
                detail="GitHub API rate limit exceeded. Please configure a GitHub token in Settings."
            )
        else:
            logger.error(f"GitHub API error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=400, detail=f"GitHub API error: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to connect to GitHub API")
    
    # Check if user is already being monitored
    existing_user = db.query(GitHubUser).filter(
        GitHubUser.github_id == user_info["id"],
        GitHubUser.added_by_user_id == current_user.id
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="GitHub user already being monitored")
    
    # Create new GitHub user record
    github_user = GitHubUser(
        username=user_info["login"],
        github_id=user_info["id"],
        display_name=user_info.get("name"),
        email=user_info.get("email"),
        avatar_url=user_info.get("avatar_url"),
        bio=user_info.get("bio"),
        company=user_info.get("company"),
        location=user_info.get("location"),
        blog=user_info.get("blog"),
        public_repos=user_info.get("public_repos", 0),
        public_gists=user_info.get("public_gists", 0),
        followers=user_info.get("followers", 0),
        following=user_info.get("following", 0),
        added_by_user_id=current_user.id
    )
    
    db.add(github_user)
    db.commit()
    db.refresh(github_user)
    
    return github_user

@router.get("/users/{user_id}/repositories", response_model=List[RepositorySelectionResponse])
async def get_user_repositories(
    user_id: int,
    refresh: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get repositories for a GitHub user with selection status"""
    github_user = db.query(GitHubUser).filter(
        GitHubUser.id == user_id,
        GitHubUser.added_by_user_id == current_user.id
    ).first()
    
    if not github_user:
        raise HTTPException(status_code=404, detail="GitHub user not found")
    
    # If refresh is requested, fetch latest repositories from GitHub
    if refresh:
        github_client = GitHubClient(current_user.github_token)
        
        try:
            repos = await github_client.get_user_repositories(github_user.username)
            
            # Update or create repository selections
            for repo_data in repos:
                existing_selection = db.query(RepositorySelection).filter(
                    RepositorySelection.github_repo_id == repo_data["id"],
                    RepositorySelection.github_user_id == user_id
                ).first()
                
                if not existing_selection:
                    selection = RepositorySelection(
                        github_repo_id=repo_data["id"],
                        name=repo_data["name"],
                        full_name=repo_data["full_name"],
                        description=repo_data.get("description"),
                        url=repo_data["html_url"],
                        clone_url=repo_data["clone_url"],
                        default_branch=repo_data.get("default_branch", "main"),
                        is_private=repo_data.get("private", False),
                        is_fork=repo_data.get("fork", False),
                        is_archived=repo_data.get("archived", False),
                        stargazers_count=repo_data.get("stargazers_count", 0),
                        watchers_count=repo_data.get("watchers_count", 0),
                        forks_count=repo_data.get("forks_count", 0),
                        size=repo_data.get("size", 0),
                        language=repo_data.get("language"),
                        github_user_id=user_id,
                        selected_by_user_id=current_user.id,
                        status=SelectionStatus.PENDING
                    )
                    db.add(selection)
            
            db.commit()
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to fetch repositories: {str(e)}")
    
    # Get existing selections
    selections = db.query(RepositorySelection).filter(
        RepositorySelection.github_user_id == user_id
    ).all()
    
    return selections

class BulkSelectionUpdate(BaseModel):
    repository_ids: List[int]
    status: str  # "selected" or "deselected"

@router.post("/users/{user_id}/repositories/bulk-update")
async def bulk_update_repository_selections(
    user_id: int,
    update_data: BulkSelectionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk update repository selection status (tick/untick repositories)"""
    github_user = db.query(GitHubUser).filter(
        GitHubUser.id == user_id,
        GitHubUser.added_by_user_id == current_user.id
    ).first()
    
    if not github_user:
        raise HTTPException(status_code=404, detail="GitHub user not found")
    
    # Validate status
    try:
        status = SelectionStatus(update_data.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    # Update selections
    updated_count = db.query(RepositorySelection).filter(
        RepositorySelection.id.in_(update_data.repository_ids),
        RepositorySelection.github_user_id == user_id
    ).update(
        {
            RepositorySelection.status: status,
            RepositorySelection.selected_at: func.now() if status == SelectionStatus.SELECTED else None
        },
        synchronize_session=False
    )
    
    db.commit()
    
    # If repositories were deselected, trigger cleanup task
    if status == SelectionStatus.DESELECTED:
        try:
            cleanup_deselected_repositories.delay(current_user.id)
            logger.info(f"Triggered cleanup task for deselected repositories for user {current_user.id}")
        except Exception as e:
            logger.warning(f"Failed to trigger cleanup task: {str(e)}")
    
    
    return {"message": f"Updated {updated_count} repository selections"}

@router.post("/users/{user_id}/repositories/sync-selected")
async def sync_selected_repositories(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync selected repositories to the main repositories table for monitoring"""
    from app.models.repository import Repository, RepositoryProvider
    from app.background.tasks import sync_repository
    
    github_user = db.query(GitHubUser).filter(
        GitHubUser.id == user_id,
        GitHubUser.added_by_user_id == current_user.id
    ).first()
    
    if not github_user:
        raise HTTPException(status_code=404, detail="GitHub user not found")
    
    # Get selected repositories that haven't been synced yet
    selected_repos = db.query(RepositorySelection).filter(
        RepositorySelection.github_user_id == user_id,
        RepositorySelection.status == SelectionStatus.SELECTED,
        RepositorySelection.repository_id.is_(None)  # Not yet synced
    ).all()
    
    synced_count = 0
    
    for selection in selected_repos:
        # Check if repository already exists
        existing_repo = db.query(Repository).filter(
            Repository.url == selection.url,
            Repository.owner_id == current_user.id
        ).first()
        
        if not existing_repo:
            # Create new repository record
            repository = Repository(
                name=selection.name,
                full_name=selection.full_name,
                url=selection.url,
                clone_url=selection.clone_url,
                provider=RepositoryProvider.GITHUB,
                external_id=str(selection.github_repo_id),
                description=selection.description,
                default_branch=selection.default_branch,
                is_private=selection.is_private,
                owner_id=current_user.id,
                sync_status="pending"
            )
            
            db.add(repository)
            db.flush()  # To get the ID
            
            # Link the selection to the repository
            selection.repository_id = repository.id
            selection.status = SelectionStatus.SYNCED
            
            # Trigger background sync (optional - can be done later)
            try:
                sync_repository.delay(repository.id)
            except Exception as e:
                logger.warning(f"Failed to queue background sync task: {str(e)}")
            
            synced_count += 1
        else:
            # Link existing repository
            selection.repository_id = existing_repo.id
            selection.status = SelectionStatus.SYNCED
    
    db.commit()
    
    return {"message": f"Synced {synced_count} repositories for monitoring"}

@router.delete("/users/{user_id}")
async def remove_github_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a GitHub user from monitoring"""
    github_user = db.query(GitHubUser).filter(
        GitHubUser.id == user_id,
        GitHubUser.added_by_user_id == current_user.id
    ).first()
    
    if not github_user:
        raise HTTPException(status_code=404, detail="GitHub user not found")
    
    # Remove associated repository selections
    db.query(RepositorySelection).filter(
        RepositorySelection.github_user_id == user_id
    ).delete()
    
    db.delete(github_user)
    db.commit()
    
    return {"message": f"GitHub user {github_user.username} removed successfully"}

# GitHub Organization Management
@router.get("/organizations", response_model=List[GitHubOrgResponse])
async def get_github_organizations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all GitHub organizations being monitored by the current user"""
    github_orgs = db.query(GitHubOrganization).filter(
        GitHubOrganization.added_by_user_id == current_user.id
    ).all()
    return github_orgs

@router.post("/organizations/connect")
async def connect_github_organization(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start GitHub OAuth flow to connect an organization"""
    if not settings.github_client_id:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
    
    # Generate state parameter for security
    state = secrets.token_urlsafe(32)
    
    # Extended scopes for organization access
    org_scopes = "repo,read:org,read:user,user:email,admin:org"
    
    params = {
        'client_id': settings.github_client_id,
        'redirect_uri': settings.github_oauth_redirect_uri,
        'scope': org_scopes,
        'state': state,
        'allow_signup': 'false'
    }
    
    github_auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    
    return {
        "auth_url": github_auth_url,
        "state": state,
        "type": "organization"
    }

@router.post("/organizations/oauth-callback")
async def github_organization_oauth_callback(
    code: str,
    state: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Handle GitHub OAuth callback for organization access"""
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
    
    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_oauth_redirect_uri,
                "state": state
            }
        )
        
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code for token")
        
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")
    
    # Get user's organizations with the access token
    github_client = GitHubClient(access_token)
    
    try:
        organizations = await github_client.get_user_organizations()
        
        # Store organizations the user has access to
        stored_orgs = []
        for org_data in organizations:
            # Check if organization already exists
            existing_org = db.query(GitHubOrganization).filter(
                GitHubOrganization.github_id == org_data["id"],
                GitHubOrganization.added_by_user_id == current_user.id
            ).first()
            
            if not existing_org:
                github_org = GitHubOrganization(
                    login=org_data["login"],
                    github_id=org_data["id"],
                    display_name=org_data.get("name"),
                    description=org_data.get("description"),
                    email=org_data.get("email"),
                    avatar_url=org_data.get("avatar_url"),
                    blog=org_data.get("blog"),
                    location=org_data.get("location"),
                    company=org_data.get("company"),
                    public_repos=org_data.get("public_repos", 0),
                    public_gists=org_data.get("public_gists", 0),
                    followers=org_data.get("followers", 0),
                    following=org_data.get("following", 0),
                    access_token=access_token,  # Store the OAuth token
                    scopes=token_data.get("scope", ""),
                    added_by_user_id=current_user.id
                )
                
                db.add(github_org)
                stored_orgs.append(github_org)
            else:
                # Update access token
                existing_org.access_token = access_token
                existing_org.scopes = token_data.get("scope", "")
                stored_orgs.append(existing_org)
        
        db.commit()
        
        return {
            "message": f"Successfully connected {len(stored_orgs)} organizations",
            "organizations": [{"id": org.id, "login": org.login, "display_name": org.display_name} for org in stored_orgs]
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch organizations: {str(e)}")

@router.get("/organizations/{org_id}/repositories", response_model=List[RepositorySelectionResponse])
async def get_organization_repositories(
    org_id: int,
    refresh: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get repositories for a GitHub organization with selection status"""
    github_org = db.query(GitHubOrganization).filter(
        GitHubOrganization.id == org_id,
        GitHubOrganization.added_by_user_id == current_user.id
    ).first()
    
    if not github_org:
        raise HTTPException(status_code=404, detail="GitHub organization not found")
    
    # If refresh is requested, fetch latest repositories from GitHub
    if refresh:
        if not github_org.access_token:
            raise HTTPException(status_code=400, detail="No OAuth token available for this organization")
            
        github_client = GitHubClient(github_org.access_token)
        
        try:
            repos = await github_client.get_organization_repositories(github_org.login)
            
            # Update or create repository selections
            for repo_data in repos:
                existing_selection = db.query(RepositorySelection).filter(
                    RepositorySelection.github_repo_id == repo_data["id"],
                    RepositorySelection.github_organization_id == org_id
                ).first()
                
                if not existing_selection:
                    selection = RepositorySelection(
                        github_repo_id=repo_data["id"],
                        name=repo_data["name"],
                        full_name=repo_data["full_name"],
                        description=repo_data.get("description"),
                        url=repo_data["html_url"],
                        clone_url=repo_data["clone_url"],
                        default_branch=repo_data.get("default_branch", "main"),
                        is_private=repo_data.get("private", False),
                        is_fork=repo_data.get("fork", False),
                        is_archived=repo_data.get("archived", False),
                        stargazers_count=repo_data.get("stargazers_count", 0),
                        watchers_count=repo_data.get("watchers_count", 0),
                        forks_count=repo_data.get("forks_count", 0),
                        size=repo_data.get("size", 0),
                        language=repo_data.get("language"),
                        github_organization_id=org_id,
                        selected_by_user_id=current_user.id,
                        status=SelectionStatus.PENDING
                    )
                    db.add(selection)
            
            db.commit()
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to fetch repositories: {str(e)}")
    
    # Get existing selections
    selections = db.query(RepositorySelection).filter(
        RepositorySelection.github_organization_id == org_id
    ).all()
    
    return selections

@router.post("/organizations/{org_id}/repositories/bulk-update")
async def bulk_update_organization_repository_selections(
    org_id: int,
    update_data: BulkSelectionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk update organization repository selection status"""
    github_org = db.query(GitHubOrganization).filter(
        GitHubOrganization.id == org_id,
        GitHubOrganization.added_by_user_id == current_user.id
    ).first()
    
    if not github_org:
        raise HTTPException(status_code=404, detail="GitHub organization not found")
    
    # Validate status
    try:
        status = SelectionStatus(update_data.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    # Update selections
    updated_count = db.query(RepositorySelection).filter(
        RepositorySelection.id.in_(update_data.repository_ids),
        RepositorySelection.github_organization_id == org_id
    ).update(
        {
            RepositorySelection.status: status,
            RepositorySelection.selected_at: func.now() if status == SelectionStatus.SELECTED else None
        },
        synchronize_session=False
    )
    
    db.commit()
    
    # If repositories were deselected, trigger cleanup task
    if status == SelectionStatus.DESELECTED:
        try:
            cleanup_deselected_repositories.delay(current_user.id)
            logger.info(f"Triggered cleanup task for deselected repositories for user {current_user.id}")
        except Exception as e:
            logger.warning(f"Failed to trigger cleanup task: {str(e)}")
    
    
    return {"message": f"Updated {updated_count} repository selections"}

@router.post("/organizations/{org_id}/repositories/sync-selected")
async def sync_selected_organization_repositories(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync selected organization repositories to the main repositories table for monitoring"""
    from app.models.repository import Repository, RepositoryProvider
    from app.background.tasks import sync_repository
    
    github_org = db.query(GitHubOrganization).filter(
        GitHubOrganization.id == org_id,
        GitHubOrganization.added_by_user_id == current_user.id
    ).first()
    
    if not github_org:
        raise HTTPException(status_code=404, detail="GitHub organization not found")
    
    # Get selected repositories that haven't been synced yet
    selected_repos = db.query(RepositorySelection).filter(
        RepositorySelection.github_organization_id == org_id,
        RepositorySelection.status == SelectionStatus.SELECTED,
        RepositorySelection.repository_id.is_(None)  # Not yet synced
    ).all()
    
    synced_count = 0
    
    for selection in selected_repos:
        # Check if repository already exists
        existing_repo = db.query(Repository).filter(
            Repository.url == selection.url,
            Repository.owner_id == current_user.id
        ).first()
        
        if not existing_repo:
            # Create new repository record
            repository = Repository(
                name=selection.name,
                full_name=selection.full_name,
                url=selection.url,
                clone_url=selection.clone_url,
                provider=RepositoryProvider.GITHUB,
                external_id=str(selection.github_repo_id),
                description=selection.description,
                default_branch=selection.default_branch,
                is_private=selection.is_private,
                owner_id=current_user.id,
                sync_status="pending"
            )
            
            db.add(repository)
            db.flush()  # To get the ID
            
            # Link the selection to the repository
            selection.repository_id = repository.id
            selection.status = SelectionStatus.SYNCED
            
            # Trigger background sync (optional - can be done later)
            try:
                sync_repository.delay(repository.id)
            except Exception as e:
                logger.warning(f"Failed to queue background sync task: {str(e)}")
            
            synced_count += 1
        else:
            # Link existing repository
            selection.repository_id = existing_repo.id
            selection.status = SelectionStatus.SYNCED
    
    db.commit()
    
    return {"message": f"Synced {synced_count} repositories for monitoring"}

@router.delete("/organizations/{org_id}")
async def remove_github_organization(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a GitHub organization from monitoring"""
    github_org = db.query(GitHubOrganization).filter(
        GitHubOrganization.id == org_id,
        GitHubOrganization.added_by_user_id == current_user.id
    ).first()
    
    if not github_org:
        raise HTTPException(status_code=404, detail="GitHub organization not found")
    
    # Remove associated repository selections
    db.query(RepositorySelection).filter(
        RepositorySelection.github_organization_id == org_id
    ).delete()
    
    db.delete(github_org)
    db.commit()
    
    return {"message": f"GitHub organization {github_org.login} removed successfully"}

# Background Task Management Endpoints
@router.post("/cleanup/deselected")
async def trigger_deselected_cleanup(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually trigger cleanup of deselected repositories"""
    try:
        task = cleanup_deselected_repositories.delay(current_user.id)
        
        return {
            "message": "Cleanup task started",
            "task_id": task.id
        }
    except Exception as e:
        logger.error(f"Failed to start cleanup task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start cleanup task")

@router.post("/cleanup/orphaned")
async def trigger_orphaned_cleanup(
    current_user: User = Depends(get_current_user)
):
    """Manually trigger cleanup of orphaned data (admin only)"""
    # TODO: Add admin check when user roles are implemented
    try:
        task = cleanup_orphaned_data.delay()
        
        return {
            "message": "Orphaned data cleanup task started",
            "task_id": task.id
        }
    except Exception as e:
        logger.error(f"Failed to start orphaned cleanup task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start cleanup task")

@router.get("/tasks/{task_id}/status")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get status of a background task"""
    try:
        from celery.result import AsyncResult
        from app.background.celery_app import celery_app
        
        result = AsyncResult(task_id, app=celery_app)
        
        if result.state == 'PENDING':
            response = {
                'state': result.state,
                'progress': 0,
                'status': 'Task is waiting to be processed'
            }
        elif result.state == 'PROGRESS':
            response = {
                'state': result.state,
                'progress': result.info.get('progress', 0),
                'status': result.info.get('status', ''),
                'current': result.info.get('current', 0),
                'total': result.info.get('total', 0)
            }
        elif result.state == 'SUCCESS':
            response = {
                'state': result.state,
                'progress': 100,
                'status': 'Task completed successfully',
                'result': result.result
            }
        else:  # FAILURE
            response = {
                'state': result.state,
                'progress': 0,
                'status': 'Task failed',
                'error': str(result.info)
            }
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get task status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get task status")