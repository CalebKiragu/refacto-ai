import asyncio
from fastapi import FastAPI
import uvicorn
from src.app.main import app, app_state

class CustomServer(uvicorn.Server):
    def __init__(self, config):
        super().__init__(config)
        self.should_exit = False

    async def serve(self, sockets=None):
        app_state.server = self
        await super().serve(sockets=sockets)

async def main():
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        lifespan="on",
        reload=True,
        log_level="debug"
    )
    server = CustomServer(config)
    
    try:
        await server.serve()
    except asyncio.CancelledError:
        pass
    finally:
        if not server.should_exit:
            server.should_exit = True
            await server.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        print("Server terminated successfully")