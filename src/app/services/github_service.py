from github import Github
from github import Auth
from typing import Optional
from ..config import settings

class GitHubService:
    def __init__(self, access_token: Optional[str] = None):
        auth = Auth.Token(access_token or settings.github_token)
        self.client = Github(auth=auth)
    
    async def create_documentation_pr(self, repo_name: str, branch: str, changes: dict):
        """Create PR with documentation updates"""
        repo = self.client.get_repo(repo_name)
        main_branch = repo.default_branch
        
        # Create new branch
        sb = repo.get_branch(main_branch)
        repo.create_git_ref(
            ref=f"refs/heads/{branch}",
            sha=sb.commit.sha
        )
        
        # Create commits for each file change
        for file_path, new_content in changes.items():
            repo.update_file(
                path=file_path,
                message=f"docs: Auto-document {file_path}",
                content=new_content,
                branch=branch,
                sha=repo.get_contents(file_path, ref=main_branch).sha
            )
        
        # Create PR
        pr = repo.create_pull(
            title=f"Auto-generated documentation updates",
            body="Automated code documentation improvements",
            head=branch,
            base=main_branch
        )
        
        return pr.html_url