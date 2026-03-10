# agent_registry/server.py
from typing import List, Optional
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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in register: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in full update: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.patch("/rest/a2a-t/v1/update_agent_partial/{name}", response_model=bool, summary="Partial update of an agent")
async def update_agent_partial(
        name: str = Path(..., description="Agent name"),
        organization: str = Query(..., description="Agent organization"),
        updates: dict = Body(..., description="Fields to update")
):
    """
    Partially update an existing agent. The name and organization cannot be changed.
    Returns True if updated, False if agent not found.
    """
    try:
        success = registry.update(name, organization, updates, partial=True)
        if not success:
            raise HTTPException(status_code=404, detail="Agent not found")
        return success
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in partial update: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


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
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/rest/a2a-t/v1/list_agents_exact", response_model=List[AgentCard], summary="Exact search")
async def list_agents_exact(
        name: Optional[str] = Query(None, description="Exact agent name"),
        organization: Optional[str] = Query(None, description="Exact organization"),
        provider: Optional[str] = Query(None, description="Exact provider (organization)")
):
    """
    Search agents by exact fields (AND combination). All parameters optional.
    If no parameters provided, returns all agents.
    """
    try:
        agents = registry.find_exact(name=name, organization=organization, provider=provider)
        return agents
    except Exception as e:
        logger.error(f"Error in exact search: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


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
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/rest/a2a-t/v1/agents/{name}", response_model=AgentCard, summary="Get agent by exact name and organization")
async def get_agent(
        name: str = Path(..., description="Agent name"),
        organization: str = Query(..., description="Agent organization")
):
    """
    Retrieve a single agent by its unique key (name + organization).
    """
    agent = registry.get(name, organization)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@app.get("/rest/a2a-t/v1/health", summary="Health check")
async def health_check():
    return {"status": "ok"}
