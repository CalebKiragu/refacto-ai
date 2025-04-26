import hmac
from fastapi import Request
from ..config import settings

async def verify_signature(request: Request) -> bool:
    secret = settings.webhook_secret.encode()
    signature = request.headers.get("X-Hub-Signature-256", "").replace("sha256=", "")
    body = await request.body()
    expected = hmac.new(secret, body, "sha256").hexdigest()
    return hmac.compare_digest(signature, expected)