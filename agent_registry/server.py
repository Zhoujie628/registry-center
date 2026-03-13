# agent_registry/server.py
from typing import List
from fastapi import FastAPI, HTTPException, Query, Path, Body
from a2a.types import AgentCard
from loguru import logger

from agent_registry.core import RegistryCore
from agent_registry.config import DEFAULT_LLM_TYPE, PERSISTENCE_FILE

app = FastAPI(
    title="Agent Registry Service",
    description="RESTful API for managing AI Agent cards with persistence and semantic search.",
    version="2.0.0"
)

# Global registry instance (singleton)
registry = RegistryCore(llm_type=DEFAULT_LLM_TYPE, persistence_file=PERSISTENCE_FILE)


@app.post("/rest/a2a-t/v1/agent-register", response_model=bool, summary="Register a new agent")
async def register_agent(agent: AgentCard):
    """
    Register a new agent. The combination (name, provider.organization) must be unique.
    Returns True if registered, False if duplicate.
    """
    try:
        success = registry.register(agent)
        return success
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Unexpected error in register: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.put("/rest/a2a-t/v1/update_agent/{name}", response_model=bool, summary="Full update (replace) an agent")
async def update_agent_full(
        name: str = Path(..., description="Agent name"),
        organization: str = Query(..., description="Agent organization"),
        agent_data: AgentCard = Body(..., description="Full agent data")
):
    """
    Fully replace an existing agent. The name and organization in the body must match the path/query.
    Returns True if updated, False if agent not found.
    """
    try:
        # Convert to dict for update
        data = agent_data.model_dump()
        success = registry.update(name, organization, data, partial=False)
        if not success:
            raise HTTPException(status_code=404, detail="Agent not found")
        return success
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException as e:
        # 捕获已经定义的 HTTPException，避免被 except Exception 捕获
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in full update: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.delete("/rest/a2a-t/v1/deregister_agent/{name}", response_model=bool, summary="Deregister an agent")
async def deregister_agent(
        name: str = Path(..., description="Agent name"),
        organization: str = Query(..., description="Agent organization")
):
    """
    Remove an agent from the registry.
    Returns True if deleted, False if not found.
    """
    try:
        success = registry.deregister(name, organization)
        if not success:
            raise HTTPException(status_code=404, detail="Agent not found")
        return success
    except Exception as e:
        logger.error(f"Unexpected error in deregister: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/rest/a2a-t/v1/agents/search", response_model=List[AgentCard], summary="Fuzzy search by task")
async def search_agents_by_task(
        task: str = Query(..., description="Natural language task description")
):
    """
    Find agents that are semantically relevant to the given task using LLM.
    """
    try:
        agents = registry.find_by_task(task)
        return agents
    except Exception as e:
        logger.error(f"Error in fuzzy search: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/rest/a2a-t/v1/health", summary="Health check")
async def health_check():
    return {"status": "ok"}
