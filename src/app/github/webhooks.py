from fastapi import APIRouter, Request, HTTPException
from github import GithubIntegration
from ..services.scanner import CodeScanner
from ..services.documenter import DocumentationGenerator
from ..services.github_service import GitHubService
from ..utils.cache import cache
from ..utils.security import verify_signature
import asyncio

router = APIRouter()

@router.post("/webhook")
async def handle_webhook(request: Request):
    payload = await request.json()
    event = request.headers.get("X-GitHub-Event")
    
    # Verify webhook signature
    if not verify_signature(request):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Route events
    if event == "push":
        await handle_push_event(payload)
    elif event == "pull_request":
        await handle_pr_event(payload)
    
    return {"status": "processing"}

async def handle_push_event(payload: dict):
    """Trigger scan on push to main branch"""
    if payload["ref"] == f"refs/heads/{payload['repository']['default_branch']}":
        repo_name = payload["repository"]["full_name"]
        await trigger_scan(repo_name)

async def handle_pr_event(payload: dict):
    """Trigger scan on new PR"""
    if payload["action"] in ["opened", "synchronize"]:
        repo_name = payload["repository"]["full_name"]
        await trigger_scan(repo_name)

async def trigger_scan(repo_name: str):
    """Execute documentation workflow"""
    installation_id = payload["installation"]["id"]
    
    # Get authenticated client
    github_app = GithubIntegration(
        app_id=settings.github_app_id,
        private_key=settings.github_private_key
    )
    access_token = github_app.get_access_token(installation_id)
    github_service = GitHubService(access_token.token)
    
    # Run scanning workflow
    scanner = CodeScanner(github_service.client)
    analysis = await scanner.scan_repository(repo_name)
    
    if analysis.needs_docs:
        documenter = DocumentationGenerator()
        documented = await documenter.generate_documentation(analysis)
        await github_service.commit_changes(repo_name, documented)