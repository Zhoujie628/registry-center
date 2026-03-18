# agent_registry/start.py
from agent_registry.server import app
import uvicorn


def main():
    uvicorn.run(app, host="0.0.0.0", port=5000, log_config=None)


if __name__ == "__main__":
    main()
