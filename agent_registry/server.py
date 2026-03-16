# agent_registry/server.py
from typing import List

from a2a.types import AgentCard
from fastapi import FastAPI, HTTPException, Query, Path, Body, Request, Depends
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette import status
from starlette.responses import Response

from agent_registry.config import (DEFAULT_LLM_TYPE,
                                   PERSISTENCE_FILE,
                                   MAX_REQUEST_BODY_SIZE,
                                   MAX_URL_LENGTH,
                                   MAX_REQUEST_RATE)
from agent_registry.core import RegistryCore
from agent_registry.model.validated_agentcard import ValidatedAgentCard

# --- Configuration & Setup ---
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="Agent Registry Service",
    description="RESTful API for managing AI Agent cards with persistence and semantic search.",
    version="2.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# --- Dependency Injection ---
def get_registry() -> RegistryCore:
    return RegistryCore(llm_type=DEFAULT_LLM_TYPE, persistence_file=PERSISTENCE_FILE)


# --- Middleware ---
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # Content Length Check
    if request.method in ("POST", "PUT"):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_REQUEST_BODY_SIZE:
            return Response(content="Payload Too Large", status_code=status.HTTP_413_CONTENT_TOO_LARGE)

    # URL Length Check (Optimized)
    if len(str(request.url.path) + str(request.query_params)) > MAX_URL_LENGTH:
        return Response(content="URI Too Long", status_code=status.HTTP_414_URI_TOO_LONG)

    return await call_next(request)


# --- Routes ---
@app.post("/rest/a2a-t/v1/agent-register", response_model=bool, summary="Register a new agent")
@limiter.limit(MAX_REQUEST_RATE)
async def register_agent(
        request: Request,
        agent: ValidatedAgentCard,
        registry: RegistryCore = Depends(get_registry)
):
    """
    Register a new agent. The combination (name, provider.organization) must be unique.
    Returns True if registered, False if duplicate.
    """
    try:
        success = await registry.register(agent)
        return success
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Unexpected error in register: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


@app.put("/rest/a2a-t/v1/update_agent/{name}", response_model=bool, summary="Full update (replace) an agent")
@limiter.limit(MAX_REQUEST_RATE)
async def update_agent_full(
        request: Request,
        name: str = Path(..., description="Agent name"),
        organization: str = Query(..., description="Agent organization"),
        agent_data: ValidatedAgentCard = Body(..., description="Full agent data"),
        registry: RegistryCore = Depends(get_registry)
):
    """
    Fully replace an existing agent. The name and organization in the body must match the path/query.
    Returns True if updated, False if agent not found.
    """
    try:
        success = await registry.update(name, organization, agent_data.model_dump(), partial=False)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        return success
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except HTTPException as e:
        # 捕获已经定义的 HTTPException，避免被 except Exception 捕获
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in full update: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


@app.delete("/rest/a2a-t/v1/deregister_agent/{name}", response_model=bool, summary="Deregister an agent")
async def deregister_agent(
        name: str = Path(..., description="Agent name"),
        organization: str = Query(..., description="Agent organization"),
        registry: RegistryCore = Depends(get_registry)
):
    """
    Remove an agent from the registry.
    Returns True if deleted, False if not found.
    """
    try:
        success = await registry.deregister(name, organization)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        return success
    except HTTPException as e:
        # 捕获已经定义的 HTTPException，避免被 except Exception 捕获
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in deregister: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


@app.get("/rest/a2a-t/v1/agents/search", response_model=List[AgentCard], summary="Fuzzy search by task")
async def search_agents_by_task(
        task: str = Query(..., description="Natural language task description"),
        registry: RegistryCore = Depends(get_registry)
):
    """
    Find agents that are semantically relevant to the given task using LLM.
    """
    try:
        agents = await registry.find_by_task(task)
        return agents
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error in fuzzy search: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


@app.get("/rest/a2a-t/v1/health", summary="Health check")
async def health_check():
    return {"status": "ok"}
