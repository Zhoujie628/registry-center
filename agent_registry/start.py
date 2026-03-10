# agent_registry/start.py
from agent_registry.server import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)