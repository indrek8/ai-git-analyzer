"""
GitHub API integration for repository syncing
"""
import httpx
from typing import List, Dict, Optional
from datetime import datetime
import logging

from app.config import settings

logger = logging.getLogger(__name__)

class GitHubClient:
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitAnalyzer/1.0"
        }
        
        if self.access_token:
            self.headers["Authorization"] = f"token {self.access_token}"
    
    async def get_repository_info(self, owner: str, repo: str) -> Dict:
        """Get basic repository information"""
        url = f"{self.base_url}/repos/{owner}/{repo}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    async def get_commits(self, owner: str, repo: str, since: Optional[datetime] = None, per_page: int = 100) -> List[Dict]:
        """Get repository commits"""
        url = f"{self.base_url}/repos/{owner}/{repo}/commits"
        params = {"per_page": per_page}
        
        if since:
            params["since"] = since.isoformat()
        
        commits = []
        page = 1
        
        async with httpx.AsyncClient() as client:
            while True:
                params["page"] = page
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                
                page_commits = response.json()
                if not page_commits:
                    break
                    
                commits.extend(page_commits)
                page += 1
                
                # Limit to prevent rate limiting
                if len(commits) >= 1000:
                    break
        
        return commits
    
    async def get_commit_details(self, owner: str, repo: str, sha: str) -> Dict:
        """Get detailed commit information including file changes"""
        url = f"{self.base_url}/repos/{owner}/{repo}/commits/{sha}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    async def get_user_repositories(self, username: str, per_page: int = 100) -> List[Dict]:
        """Get all public repositories for a GitHub user"""
        url = f"{self.base_url}/users/{username}/repos"
        params = {"per_page": per_page, "sort": "updated", "direction": "desc"}
        
        repos = []
        page = 1
        
        async with httpx.AsyncClient() as client:
            while True:
                params["page"] = page
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                
                page_repos = response.json()
                if not page_repos:
                    break
                    
                repos.extend(page_repos)
                page += 1
                
                # Limit to prevent rate limiting
                if len(repos) >= 1000:
                    break
        
        return repos
    
    async def get_organization_repositories(self, org: str, per_page: int = 100) -> List[Dict]:
        """Get all repositories for a GitHub organization"""
        url = f"{self.base_url}/orgs/{org}/repos"
        params = {"per_page": per_page, "sort": "updated", "direction": "desc"}
        
        repos = []
        page = 1
        
        async with httpx.AsyncClient() as client:
            while True:
                params["page"] = page
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                
                page_repos = response.json()
                if not page_repos:
                    break
                    
                repos.extend(page_repos)
                page += 1
                
                # Limit to prevent rate limiting
                if len(repos) >= 1000:
                    break
        
        return repos
    
    async def get_user_organizations(self, username: str = None) -> List[Dict]:
        """Get organizations for a user (or authenticated user if no username provided)"""
        if username:
            url = f"{self.base_url}/users/{username}/orgs"
        else:
            url = f"{self.base_url}/user/orgs"
            
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    def parse_repository_url(self, repo_url: str) -> tuple[str, str]:
        """Parse GitHub repository URL to extract owner and repo name"""
        # Handle various GitHub URL formats
        url = repo_url.rstrip('/')
        if url.endswith('.git'):
            url = url[:-4]
        
        # Extract from different URL formats
        if 'github.com/' in url:
            parts = url.split('github.com/')[-1].split('/')
            if len(parts) >= 2:
                return parts[0], parts[1]
        
        raise ValueError(f"Invalid GitHub repository URL: {repo_url}")

def parse_commit_data(commit_data: Dict) -> Dict:
    """Parse GitHub commit data into our internal format"""
    commit = commit_data.get('commit', {})
    author = commit.get('author', {})
    committer = commit.get('committer', {})
    
    # Parse file statistics if available
    files_changed = len(commit_data.get('files', []))
    lines_added = sum(f.get('additions', 0) for f in commit_data.get('files', []))
    lines_removed = sum(f.get('deletions', 0) for f in commit_data.get('files', []))
    
    # Parse file changes
    files_modified = []
    files_added = []
    files_deleted = []
    
    for file_data in commit_data.get('files', []):
        filename = file_data.get('filename')
        status = file_data.get('status')
        
        if status == 'added':
            files_added.append(filename)
        elif status == 'removed':
            files_deleted.append(filename)
        else:
            files_modified.append(filename)
    
    return {
        'sha': commit_data.get('sha'),
        'message': commit.get('message', ''),
        'author_name': author.get('name', ''),
        'author_email': author.get('email', ''),
        'committer_name': committer.get('name', ''),
        'committer_email': committer.get('email', ''),
        'commit_date': datetime.fromisoformat(author.get('date', '').replace('Z', '+00:00')),
        'lines_added': lines_added,
        'lines_removed': lines_removed,
        'files_changed': files_changed,
        'files_modified': files_modified,
        'files_added': files_added,
        'files_deleted': files_deleted,
        'parent_shas': [p.get('sha') for p in commit_data.get('parents', [])],
        'is_merge': len(commit_data.get('parents', [])) > 1
    }