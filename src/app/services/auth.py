import hmac
import hashlib
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..config import settings

security = HTTPBearer()

async def verify_github_webhook(request: Request) -> bool:
    """
    Verify GitHub webhook signature
    Raises HTTPException if verification fails
    """
    try:
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not signature:
            raise ValueError("Missing signature header")
            
        body = await request.body()
        secret = settings.github_webhook_secret.encode()
        
        if not secret:
            raise ValueError("Webhook secret not configured")
            
        expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
        incoming = signature.replace("sha256=", "")
        
        if not hmac.compare_digest(incoming, expected):
            raise ValueError("Invalid signature")
            
        return True
        
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Webhook verification failed: {str(e)}"
        )
    
async def verify_github_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Verify GitHub access token"""
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization token"
        )
    
    # In production, you would validate against GitHub's API
    if settings.env == "production":
        if not await _validate_with_github(token):
            raise HTTPException(
                status_code=401,
                detail="Invalid GitHub token"
            )
    
    return token

async def verify_webhook_signature(request: Request) -> bool:
    """Verify GitHub webhook signature"""
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not signature:
        raise HTTPException(
            status_code=401,
            detail="Missing signature header"
        )
    
    body = await request.body()
    secret = settings.github_webhook_secret.encode()
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(f"sha256={expected}", signature):
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature"
        )
    return True

async def _validate_with_github(token: str) -> bool:
    """Validate token with GitHub's API"""
    # Implementation would make request to:
    # GET https://api.github.com/applications/{client_id}/token
    # With basic auth using client_id and client_secret
    return True  # Placeholder for actual implementation