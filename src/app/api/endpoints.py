from fastapi import APIRouter, Depends, HTTPException
from ..services.auth import verify_github_token

router = APIRouter(dependencies=[Depends(verify_github_token)])

@router.post("/manual-scan")
async def manual_trigger(
    repo: str,
    branch: str = None,
    paths: list[str] = None
):
    """Endpoint for manual triggers from GitHub UI"""
    await start_scanning_workflow(
        repo=repo,
        branch=branch,
        paths=paths,
        trigger_source="manual"
    )
    return {"status": "scan_started"}