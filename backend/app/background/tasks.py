from celery import current_app as celery_app
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
import logging

from app.config import settings

# Set up database connection for Celery tasks
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def sync_repository(self, repository_id: int):
    """
    Background task to sync a repository
    """
    db = SessionLocal()
    try:
        from app.models.repository import Repository, RepositoryProvider
        from app.models.commit import Commit
        from app.models.developer import Developer
        from app.repositories.github import GitHubClient, parse_commit_data
        
        # Update task status
        self.update_state(state='PROGRESS', meta={'progress': 0, 'status': 'Starting sync'})
        
        # Get repository
        repository = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repository:
            raise Exception(f"Repository {repository_id} not found")
        
        # Update repository status
        repository.sync_status = "syncing"
        db.commit()
        
        self.update_state(state='PROGRESS', meta={'progress': 10, 'status': 'Connecting to repository'})
        
        if repository.provider == RepositoryProvider.GITHUB:
            import asyncio
            asyncio.run(_sync_github_repository(repository, db, self))
        else:
            raise Exception(f"Provider {repository.provider} not supported yet")
        
        # Mark as completed
        repository.sync_status = "completed"
        repository.last_synced_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Successfully synced repository {repository_id}")
        return {"status": "completed", "repository_id": repository_id}
        
    except Exception as exc:
        logger.error(f"Failed to sync repository {repository_id}: {str(exc)}")
        
        # Update repository status to failed
        repository = db.query(Repository).filter(Repository.id == repository_id).first()
        if repository:
            repository.sync_status = "failed"
            repository.sync_error = str(exc)
            db.commit()
        
        raise self.retry(exc=exc, countdown=60, max_retries=3)
    finally:
        db.close()

async def _sync_github_repository(repository, db, task_instance):
    """Sync GitHub repository data"""
    from app.models.commit import Commit
    from app.models.developer import Developer
    from app.repositories.github import GitHubClient, parse_commit_data
    
    github_client = GitHubClient()
    
    try:
        # Parse repository URL
        owner, repo_name = github_client.parse_repository_url(repository.url)
        
        task_instance.update_state(state='PROGRESS', meta={'progress': 20, 'status': 'Fetching repository info'})
        
        # Get repository info
        repo_info = await github_client.get_repository_info(owner, repo_name)
        
        # Update repository metadata
        repository.description = repo_info.get('description')
        repository.default_branch = repo_info.get('default_branch', 'main')
        repository.is_private = repo_info.get('private', False)
        
        task_instance.update_state(state='PROGRESS', meta={'progress': 30, 'status': 'Fetching commits'})
        
        # Get commits since last sync
        since_date = repository.last_synced_at
        commits_data = await github_client.get_commits(owner, repo_name, since=since_date)
        
        total_commits = len(commits_data)
        logger.info(f"Found {total_commits} commits to process")
        
        task_instance.update_state(state='PROGRESS', meta={'progress': 40, 'status': f'Processing {total_commits} commits'})
        
        processed = 0
        for commit_data in commits_data:
            # Check if commit already exists
            existing_commit = db.query(Commit).filter(
                Commit.sha == commit_data.get('sha'),
                Commit.repository_id == repository.id
            ).first()
            
            if existing_commit:
                continue
            
            # Get detailed commit info
            detailed_commit = await github_client.get_commit_details(owner, repo_name, commit_data.get('sha'))
            parsed_commit = parse_commit_data(detailed_commit)
            
            # Find or create developer
            developer = _find_or_create_developer(db, parsed_commit['author_name'], parsed_commit['author_email'])
            
            # Create commit record
            commit = Commit(
                sha=parsed_commit['sha'],
                message=parsed_commit['message'],
                author_name=parsed_commit['author_name'],
                author_email=parsed_commit['author_email'],
                committer_name=parsed_commit['committer_name'],
                committer_email=parsed_commit['committer_email'],
                commit_date=parsed_commit['commit_date'],
                repository_id=repository.id,
                developer_id=developer.id if developer else None,
                lines_added=parsed_commit['lines_added'],
                lines_removed=parsed_commit['lines_removed'],
                files_changed=parsed_commit['files_changed'],
                files_modified=parsed_commit['files_modified'],
                files_added=parsed_commit['files_added'],
                files_deleted=parsed_commit['files_deleted'],
                parent_shas=parsed_commit['parent_shas'],
                is_merge=parsed_commit['is_merge']
            )
            
            db.add(commit)
            processed += 1
            
            # Update progress
            progress = 40 + int((processed / total_commits) * 50)
            task_instance.update_state(state='PROGRESS', meta={
                'progress': progress, 
                'status': f'Processed {processed}/{total_commits} commits'
            })
            
            # Commit in batches to avoid memory issues
            if processed % 50 == 0:
                db.commit()
        
        db.commit()
        task_instance.update_state(state='PROGRESS', meta={'progress': 95, 'status': 'Finalizing sync'})
        
    except Exception as e:
        logger.error(f"Error syncing GitHub repository: {str(e)}")
        raise

def _find_or_create_developer(db, name: str, email: str):
    """Find existing developer or create new one"""
    from app.models.developer import Developer
    
    # Try to find by email first
    developer = db.query(Developer).filter(Developer.email == email).first()
    
    if not developer:
        # Create new developer
        developer = Developer(
            name=name,
            email=email,
            git_name=name,
            git_email=email
        )
        db.add(developer)
        db.flush()  # Get ID without committing
    
    return developer

@celery_app.task(bind=True)
def analyze_commits(self, repository_id: int):
    """
    Background task to analyze commits with AI
    """
    db = SessionLocal()
    try:
        from app.models.repository import Repository
        from app.models.commit import Commit
        
        self.update_state(state='PROGRESS', meta={'progress': 0, 'status': 'Starting analysis'})
        
        repository = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repository:
            raise Exception(f"Repository {repository_id} not found")
        
        # Get unanalyzed commits
        commits = db.query(Commit).filter(
            Commit.repository_id == repository_id,
            Commit.is_analyzed == False
        ).all()
        
        total_commits = len(commits)
        logger.info(f"Analyzing {total_commits} commits for repository {repository_id}")
        
        # TODO: Implement AI analysis logic
        for i, commit in enumerate(commits):
            self.update_state(
                state='PROGRESS',
                meta={
                    'progress': int((i / total_commits) * 100),
                    'status': f'Analyzing commit {i+1}/{total_commits}'
                }
            )
            
            # Mark commit as analyzed (placeholder)
            commit.is_analyzed = True
            
        db.commit()
        
        logger.info(f"Successfully analyzed {total_commits} commits for repository {repository_id}")
        return {"status": "completed", "repository_id": repository_id, "commits_analyzed": total_commits}
        
    except Exception as exc:
        logger.error(f"Failed to analyze commits for repository {repository_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)
    finally:
        db.close()

@celery_app.task(bind=True)
def bulk_sync_repositories(self, repository_ids: list, user_id: int):
    """
    Background task to sync multiple repositories in parallel with progress tracking
    """
    db = SessionLocal()
    try:
        from app.models.repository import Repository
        from app.models.user import User
        
        self.update_state(state='PROGRESS', meta={
            'progress': 0, 
            'status': 'Starting bulk sync',
            'total_repos': len(repository_ids),
            'completed_repos': 0,
            'failed_repos': 0
        })
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise Exception(f"User {user_id} not found")
        
        # Validate repositories belong to user
        repositories = db.query(Repository).filter(
            Repository.id.in_(repository_ids),
            Repository.owner_id == user_id
        ).all()
        
        if len(repositories) != len(repository_ids):
            raise Exception("Some repositories not found or not owned by user")
        
        total_repos = len(repositories)
        completed = 0
        failed = 0
        results = []
        
        # Process repositories in chunks to avoid overwhelming the system
        chunk_size = 5
        for i in range(0, total_repos, chunk_size):
            chunk = repositories[i:i + chunk_size]
            
            # Start sync tasks for this chunk
            chunk_tasks = []
            for repo in chunk:
                task = sync_repository.delay(repo.id)
                chunk_tasks.append((repo, task))
            
            # Wait for chunk to complete
            for repo, task in chunk_tasks:
                try:
                    result = task.get(timeout=300)  # 5 minute timeout per repo
                    results.append({"repository_id": repo.id, "status": "completed", "name": repo.name})
                    completed += 1
                except Exception as e:
                    results.append({"repository_id": repo.id, "status": "failed", "name": repo.name, "error": str(e)})
                    failed += 1
                
                # Update progress
                progress = int(((completed + failed) / total_repos) * 100)
                self.update_state(state='PROGRESS', meta={
                    'progress': progress,
                    'status': f'Synced {completed + failed}/{total_repos} repositories',
                    'total_repos': total_repos,
                    'completed_repos': completed,
                    'failed_repos': failed,
                    'results': results
                })
        
        logger.info(f"Bulk sync completed: {completed} successful, {failed} failed")
        return {
            "status": "completed",
            "total_repos": total_repos,
            "completed_repos": completed,
            "failed_repos": failed,
            "results": results
        }
        
    except Exception as exc:
        logger.error(f"Failed bulk sync for user {user_id}: {str(exc)}")
        raise
    finally:
        db.close()

@celery_app.task(bind=True)
def refresh_github_user_repositories(self, github_user_id: int):
    """
    Background task to refresh repository list for a GitHub user
    """
    db = SessionLocal()
    try:
        from app.models.github_user import GitHubUser
        from app.models.repository_selection import RepositorySelection, SelectionStatus
        from app.repositories.github import GitHubClient
        
        self.update_state(state='PROGRESS', meta={'progress': 0, 'status': 'Starting refresh'})
        
        github_user = db.query(GitHubUser).filter(GitHubUser.id == github_user_id).first()
        if not github_user:
            raise Exception(f"GitHub user {github_user_id} not found")
        
        # Get access token from user
        user = github_user.added_by
        github_client = GitHubClient(user.github_token)
        
        self.update_state(state='PROGRESS', meta={'progress': 20, 'status': 'Fetching repositories from GitHub'})
        
        # Fetch latest repositories
        import asyncio
        repos = asyncio.run(github_client.get_user_repositories(github_user.username))
        
        self.update_state(state='PROGRESS', meta={'progress': 50, 'status': f'Processing {len(repos)} repositories'})
        
        new_repos = 0
        updated_repos = 0
        
        for repo_data in repos:
            existing_selection = db.query(RepositorySelection).filter(
                RepositorySelection.github_repo_id == repo_data["id"],
                RepositorySelection.github_user_id == github_user_id
            ).first()
            
            if not existing_selection:
                # New repository
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
                    github_user_id=github_user_id,
                    selected_by_user_id=github_user.added_by_user_id,
                    status=SelectionStatus.PENDING
                )
                db.add(selection)
                new_repos += 1
            else:
                # Update existing repository metadata
                existing_selection.description = repo_data.get("description")
                existing_selection.stargazers_count = repo_data.get("stargazers_count", 0)
                existing_selection.watchers_count = repo_data.get("watchers_count", 0)
                existing_selection.forks_count = repo_data.get("forks_count", 0)
                existing_selection.size = repo_data.get("size", 0)
                existing_selection.language = repo_data.get("language")
                existing_selection.is_archived = repo_data.get("archived", False)
                updated_repos += 1
        
        # Update user stats
        github_user.public_repos = len(repos)
        github_user.last_synced_at = datetime.utcnow()
        
        db.commit()
        
        self.update_state(state='PROGRESS', meta={'progress': 100, 'status': 'Refresh completed'})
        
        logger.info(f"Refreshed repositories for GitHub user {github_user.username}: {new_repos} new, {updated_repos} updated")
        return {
            "status": "completed", 
            "github_user_id": github_user_id,
            "username": github_user.username,
            "new_repositories": new_repos,
            "updated_repositories": updated_repos,
            "total_repositories": len(repos)
        }
        
    except Exception as exc:
        logger.error(f"Failed to refresh GitHub user {github_user_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)
    finally:
        db.close()

@celery_app.task(bind=True)
def refresh_github_organization_repositories(self, github_org_id: int):
    """
    Background task to refresh repository list for a GitHub organization
    """
    db = SessionLocal()
    try:
        from app.models.github_organization import GitHubOrganization
        from app.models.repository_selection import RepositorySelection, SelectionStatus
        from app.repositories.github import GitHubClient
        
        self.update_state(state='PROGRESS', meta={'progress': 0, 'status': 'Starting refresh'})
        
        github_org = db.query(GitHubOrganization).filter(GitHubOrganization.id == github_org_id).first()
        if not github_org:
            raise Exception(f"GitHub organization {github_org_id} not found")
        
        if not github_org.access_token:
            raise Exception("No OAuth token available for this organization")
        
        github_client = GitHubClient(github_org.access_token)
        
        self.update_state(state='PROGRESS', meta={'progress': 20, 'status': 'Fetching repositories from GitHub'})
        
        # Fetch latest repositories
        import asyncio
        repos = asyncio.run(github_client.get_organization_repositories(github_org.login))
        
        self.update_state(state='PROGRESS', meta={'progress': 50, 'status': f'Processing {len(repos)} repositories'})
        
        new_repos = 0
        updated_repos = 0
        
        for repo_data in repos:
            existing_selection = db.query(RepositorySelection).filter(
                RepositorySelection.github_repo_id == repo_data["id"],
                RepositorySelection.github_organization_id == github_org_id
            ).first()
            
            if not existing_selection:
                # New repository
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
                    github_organization_id=github_org_id,
                    selected_by_user_id=github_org.added_by_user_id,
                    status=SelectionStatus.PENDING
                )
                db.add(selection)
                new_repos += 1
            else:
                # Update existing repository metadata
                existing_selection.description = repo_data.get("description")
                existing_selection.stargazers_count = repo_data.get("stargazers_count", 0)
                existing_selection.watchers_count = repo_data.get("watchers_count", 0)
                existing_selection.forks_count = repo_data.get("forks_count", 0)
                existing_selection.size = repo_data.get("size", 0)
                existing_selection.language = repo_data.get("language")
                existing_selection.is_archived = repo_data.get("archived", False)
                updated_repos += 1
        
        # Update organization stats
        github_org.public_repos = len(repos)
        github_org.last_synced_at = datetime.utcnow()
        
        db.commit()
        
        self.update_state(state='PROGRESS', meta={'progress': 100, 'status': 'Refresh completed'})
        
        logger.info(f"Refreshed repositories for GitHub organization {github_org.login}: {new_repos} new, {updated_repos} updated")
        return {
            "status": "completed", 
            "github_org_id": github_org_id,
            "login": github_org.login,
            "new_repositories": new_repos,
            "updated_repositories": updated_repos,
            "total_repositories": len(repos)
        }
        
    except Exception as exc:
        logger.error(f"Failed to refresh GitHub organization {github_org_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)
    finally:
        db.close()

@celery_app.task(bind=True)
def periodic_refresh_all_github_sources(self):
    """
    Periodic task to refresh all GitHub users and organizations
    """
    db = SessionLocal()
    try:
        from app.models.github_user import GitHubUser
        from app.models.github_organization import GitHubOrganization
        
        self.update_state(state='PROGRESS', meta={'progress': 0, 'status': 'Starting periodic refresh'})
        
        # Get all active GitHub users and organizations
        github_users = db.query(GitHubUser).filter(GitHubUser.is_active == True).all()
        github_orgs = db.query(GitHubOrganization).filter(GitHubOrganization.is_active == True).all()
        
        total_sources = len(github_users) + len(github_orgs)
        processed = 0
        
        logger.info(f"Starting periodic refresh of {len(github_users)} users and {len(github_orgs)} organizations")
        
        # Refresh GitHub users
        for user in github_users:
            try:
                task = refresh_github_user_repositories.delay(user.id)
                task.get(timeout=180)  # 3 minute timeout
                processed += 1
                
                progress = int((processed / total_sources) * 100)
                self.update_state(state='PROGRESS', meta={
                    'progress': progress,
                    'status': f'Refreshed {processed}/{total_sources} sources'
                })
                
            except Exception as e:
                logger.error(f"Failed to refresh GitHub user {user.username}: {str(e)}")
                processed += 1
        
        # Refresh GitHub organizations
        for org in github_orgs:
            try:
                task = refresh_github_organization_repositories.delay(org.id)
                task.get(timeout=180)  # 3 minute timeout
                processed += 1
                
                progress = int((processed / total_sources) * 100)
                self.update_state(state='PROGRESS', meta={
                    'progress': progress,
                    'status': f'Refreshed {processed}/{total_sources} sources'
                })
                
            except Exception as e:
                logger.error(f"Failed to refresh GitHub organization {org.login}: {str(e)}")
                processed += 1
        
        logger.info(f"Periodic refresh completed: {processed}/{total_sources} sources processed")
        return {
            "status": "completed",
            "total_sources": total_sources,
            "processed_sources": processed,
            "github_users": len(github_users),
            "github_orgs": len(github_orgs)
        }
        
    except Exception as exc:
        logger.error(f"Failed periodic refresh: {str(exc)}")
        raise
    finally:
        db.close()

@celery_app.task(bind=True)
def cleanup_old_tasks(self):
    """
    Cleanup old completed tasks to prevent database bloat
    """
    try:
        from celery.result import AsyncResult
        from datetime import timedelta
        
        # This would require additional setup to track task results in database
        # For now, just a placeholder that logs the cleanup attempt
        logger.info("Cleaning up old tasks (placeholder implementation)")
        
        return {"status": "completed", "cleaned_tasks": 0}
        
    except Exception as exc:
        logger.error(f"Failed to cleanup old tasks: {str(exc)}")
        raise