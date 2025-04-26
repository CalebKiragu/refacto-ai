import asyncio
import signal  
import platform
import time
from fastapi import FastAPI, BackgroundTasks, Request, Depends
from .services.scanner import CodeScanner
from .services.documenter import DocumentationGenerator
from .services.github_service import GitHubService
from .services.auth import verify_github_webhook
from contextlib import asynccontextmanager
from .utils.cache import cache  # Import cache instance
from .config import settings
from .database import init_db
from src.app.utils.cache import cache
from .utils.logging import configure_logging

class AppState:
    def __init__(self):
        self.should_exit = asyncio.Event()
        self.force_exit = False

app_state = AppState()

async def monitor_shutdown():
    """Background task to watch for shutdown signals"""
    await app_state.should_exit.wait()
    print("Shutdown signal received")
    # This will trigger the lifespan's finally block
    raise KeyboardInterrupt

 # Add signal handlers for additional safety
def handle_signal():
    """Trigger graceful shutdown"""
    print("\nReceived shutdown signal")
    app_state.should_exit.set()

# Using lifespan events (most reliable)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async context manager for startup/shutdown events"""
    # Startup
    await cache.init_redis()
    
   # Setup signal handlers
    if platform.system() != "Windows":
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, app_state.should_exit.set)
    else:
        signal.signal(signal.SIGINT, lambda s, f: app_state.should_exit.set())
    
    # Background shutdown monitor
    async def watch_for_exit():
        await app_state.should_exit.wait()
        if app_state.server:
            app_state.server.should_exit = True

    asyncio.create_task(watch_for_exit())
    
    try:
        yield
    finally:
        if app_state.should_exit:
            await cache.close()

app = FastAPI(title="Refacto AI", lifespan=lifespan)
configure_logging()

@app.on_event("startup")
async def startup():
    # Register signals (Windows compatible)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, lambda s, f: handle_signal())
    signal.signal(signal.SIGINT, lambda s, f: handle_signal())

    # Initialize services
    await init_db()
    await cache.init_redis()

@app.get('/')
async def test():
    """Test Endpoint"""
    return {"status": "ok"}

@app.get("/health")
async def health():
    """System health endpoint"""
    if app_state.should_exit.is_set():
        return {"status": "shutting down"}
    return {"status": "running"}

@app.get("/shutdown")
async def shutdown_server():
    """Manual shutdown endpoint"""
    app_state.should_exit.set()
    await cache.close()
    return {"message": "Shutdown initiated"}

@app.post("/scan-and-document")
async def scan_and_document(
    repo_name: str,
    background_tasks: BackgroundTasks
):
    """Endpoint to trigger documentation process"""
    background_tasks.add_task(run_documentation_workflow, repo_name)
    return {"status": "started", "repo": repo_name}

async def run_documentation_workflow(repo_name: str):
    """Complete documentation workflow"""
    github_service = GitHubService()
    scanner = CodeScanner(github_service.client)
    documenter = DocumentationGenerator()
    
    # Scan repository
    analysis_results = await scanner.scan_repository(repo_name)
    
    # Generate documentation
    changes = {}
    for file_path, analysis in analysis_results.items():
        if analysis.needs_docs:
            documented_code = await documenter.generate_documentation(analysis)
            changes[file_path] = documented_code
    
    # Create PR if changes found
    if changes:
        branch_name = f"docs/auto-document-{int(time.time())}"
        pr_url = await github_service.create_documentation_pr(
            repo_name,
            branch_name,
            changes
        )
        return {"pr_url": pr_url}
    
    return {"message": "No documentation needed"}

@app.post("/webhooks/github")
async def handle_github_webhook(
    request: Request, 
    verified: bool = Depends(verify_github_webhook)
):
    # Process verified webhook
    payload = await request.json()
    return {"status": "ok", "verified": verified}


