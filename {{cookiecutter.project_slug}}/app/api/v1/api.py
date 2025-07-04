"""API v1 router configuration."""

from fastapi import APIRouter

from app.api.v1.endpoints import base, user, conversation, message, agent, execution, auth, agent_execution, tools


api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(base.router, prefix="/base", tags=["base"])
api_router.include_router(user.router, prefix="/users", tags=["users"])
api_router.include_router(agent.router, prefix="/agents", tags=["agents"])
api_router.include_router(execution.router, prefix="/executions", tags=["executions"])
api_router.include_router(agent_execution.router, prefix="/agent-execution", tags=["agent-execution"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])
api_router.include_router(conversation.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(message.router, prefix="/messages", tags=["messages"])
