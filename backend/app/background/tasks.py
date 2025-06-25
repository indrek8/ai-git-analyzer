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