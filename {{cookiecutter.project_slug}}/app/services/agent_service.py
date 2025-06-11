"""
Agent Service - High-level service for AI agent management and execution.

This service provides business logic for creating, managing, and executing
AI agents with conversation context and tool integration.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.core.agent import AIAgent, AgentConfig
from app.ai.core.orchestrator import WorkflowOrchestrator
from app.ai.core.memory import MemoryManager
from app.ai.services import (
    chat_service,
    function_calling_service,
    streaming_service,
    embedding_service
)
from app.ai.tools import get_available_tools, create_tool_instance
from app.crud import conversation as conversation_crud
from app.crud import message as message_crud
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.schemas.conversation import ConversationCreate, ConversationResponse
from app.schemas.message import MessageCreate, MessageResponse
from app.core.exceptions import AIServiceError, NotFoundError

logger = logging.getLogger(__name__)


@dataclass
class AgentExecutionRequest:
    """Request for agent execution."""
    user_id: UUID
    conversation_id: Optional[UUID] = None
    message: str = ""
    agent_config: Optional[Dict[str, Any]] = None
    tools: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None
    stream: bool = False
    max_turns: int = 10
    timeout: float = 120.0


@dataclass
class AgentExecutionResult:
    """Result from agent execution."""
    conversation_id: UUID
    response_message: MessageResponse
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    tokens_used: int = 0
    execution_time: float = 0.0
    status: str = "completed"


class AgentService:
    """High-level service for AI agent operations."""
    
    def __init__(self):
        self.active_agents: Dict[str, AIAgent] = {}
        self.memory_managers: Dict[UUID, MemoryManager] = {}
        self.default_agent_config = {
            "provider": "openai",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 2000,
            "system_prompt": None,
            "tools_enabled": True,
            "memory_enabled": True,
            "max_memory_items": 1000
        }
    
    async def create_conversation(
        self,
        db: AsyncSession,
        user_id: UUID,
        title: Optional[str] = None
    ) -> ConversationResponse:
        """
        Create a new conversation for an agent session.
        
        Args:
            db: Database session
            user_id: User ID
            title: Optional conversation title
            
        Returns:
            ConversationResponse object
        """
        conversation_data = ConversationCreate(
            title=title or f"Agent Chat - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            user_id=user_id
        )
        
        conversation = await conversation_crud.create(db, obj_in=conversation_data)
        return ConversationResponse.from_orm(conversation)
    
    async def get_or_create_agent(
        self,
        conversation_id: UUID,
        config: Optional[Dict[str, Any]] = None
    ) -> AIAgent:
        """
        Get existing agent or create new one for conversation.
        
        Args:
            conversation_id: Conversation ID
            config: Agent configuration
            
        Returns:
            AIAgent instance
        """
        agent_key = str(conversation_id)
        
        if agent_key in self.active_agents:
            return self.active_agents[agent_key]
        
        # Merge with default config
        agent_config = {**self.default_agent_config}
        if config:
            agent_config.update(config)
        
        # Create agent configuration
        config_obj = AgentConfig(
            name=f"agent_{conversation_id}",
            provider=agent_config["provider"],
            model=agent_config["model"],
            temperature=agent_config["temperature"],
            max_tokens=agent_config["max_tokens"],
            system_prompt=agent_config.get("system_prompt"),
            tools_enabled=agent_config["tools_enabled"],
            memory_enabled=agent_config["memory_enabled"]
        )
        
        # Create agent
        agent = AIAgent(config=config_obj)
        
        # Set up memory if enabled
        if config_obj.memory_enabled:
            memory_manager = MemoryManager(
                agent_id=str(conversation_id),
                max_items=agent_config["max_memory_items"]
            )
            self.memory_managers[conversation_id] = memory_manager
            agent.memory = memory_manager
        
        # Register tools if enabled
        if config_obj.tools_enabled:
            available_tools = get_available_tools()
            tool_names = agent_config.get("tools", list(available_tools.keys()))
            
            for tool_name in tool_names:
                if tool_name in available_tools:
                    tool_instance = create_tool_instance(tool_name)
                    if tool_instance:
                        function_calling_service.register_tool(tool_instance)
        
        self.active_agents[agent_key] = agent
        return agent
    
    async def execute_agent(
        self,
        db: AsyncSession,
        request: AgentExecutionRequest
    ) -> Union[AgentExecutionResult, AsyncGenerator]:
        """
        Execute agent with user message.
        
        Args:
            db: Database session
            request: Agent execution request
            
        Returns:
            AgentExecutionResult or AsyncGenerator for streaming
        """
        import time
        start_time = time.time()
        
        try:
            # Get or create conversation
            if request.conversation_id:
                conversation = await conversation_crud.get(db, id=request.conversation_id)
                if not conversation:
                    raise NotFoundError(f"Conversation {request.conversation_id} not found")
            else:
                conversation_response = await self.create_conversation(
                    db, request.user_id, title="Agent Chat"
                )
                conversation = await conversation_crud.get(db, id=conversation_response.id)
                request.conversation_id = conversation.id
            
            # Create user message
            user_message_data = MessageCreate(
                content=request.message,
                role=MessageRole.USER,
                conversation_id=request.conversation_id
            )
            user_message = await message_crud.create(db, obj_in=user_message_data)
            
            # Get or create agent
            agent = await self.get_or_create_agent(
                request.conversation_id,
                request.agent_config
            )
            
            # Load conversation history for context
            conversation_messages = await message_crud.get_by_conversation(
                db, conversation_id=request.conversation_id
            )
            
            # Convert to chat messages
            chat_history = []
            for msg in conversation_messages[:-1]:  # Exclude the just-created user message
                chat_history.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
            
            # Add current user message
            chat_history.append({
                "role": "user",
                "content": request.message
            })
            
            # Execute agent
            if request.stream:
                return await self._execute_agent_streaming(
                    db, agent, chat_history, request
                )
            else:
                return await self._execute_agent_sync(
                    db, agent, chat_history, request, start_time
                )
                
        except Exception as e:
            logger.error(f"Agent execution failed: {str(e)}")
            raise AIServiceError(f"Agent execution error: {str(e)}")
    
    async def _execute_agent_sync(
        self,
        db: AsyncSession,
        agent: AIAgent,
        chat_history: List[Dict[str, str]],
        request: AgentExecutionRequest,
        start_time: float
    ) -> AgentExecutionResult:
        """Execute agent synchronously."""
        import time
        
        # Execute agent
        execution_context = {
            "conversation_id": str(request.conversation_id),
            "user_id": str(request.user_id),
            "max_turns": request.max_turns,
            **(request.context or {})
        }
        
        result = await agent.process_message(
            message=request.message,
            context=execution_context,
            chat_history=chat_history
        )
        
        # Create assistant message
        assistant_message_data = MessageCreate(
            content=result.response,
            role=MessageRole.ASSISTANT,
            conversation_id=request.conversation_id,
            metadata={
                "tool_calls": result.tool_calls,
                "tokens_used": result.tokens_used,
                "execution_time": result.execution_time
            }
        )
        assistant_message = await message_crud.create(db, obj_in=assistant_message_data)
        
        execution_time = time.time() - start_time
        
        return AgentExecutionResult(
            conversation_id=request.conversation_id,
            response_message=MessageResponse.from_orm(assistant_message),
            tool_calls=result.tool_calls,
            execution_metadata=result.metadata,
            tokens_used=result.tokens_used,
            execution_time=execution_time,
            status="completed"
        )
    
    async def _execute_agent_streaming(
        self,
        db: AsyncSession,
        agent: AIAgent,
        chat_history: List[Dict[str, str]],
        request: AgentExecutionRequest
    ):
        """Execute agent with streaming response."""
        from app.ai.services.streaming_service import StreamingRequest, StreamEventType
        from app.ai.providers.base import ChatMessage
        
        # Convert chat history to ChatMessage objects
        messages = []
        for msg in chat_history:
            messages.append(ChatMessage(
                role=msg["role"],
                content=msg["content"]
            ))
        
        # Create streaming request
        streaming_request = StreamingRequest(
            messages=messages,
            provider=agent.config.provider,
            model=agent.config.model,
            temperature=agent.config.temperature,
            max_tokens=agent.config.max_tokens,
            functions=function_calling_service.get_function_definitions(),
            include_function_execution=True,
            stream_function_calls=True
        )
        
        # Stream response
        full_response = ""
        tool_calls = []
        
        async def stream_generator():
            nonlocal full_response, tool_calls
            
            async for event in streaming_service.stream_chat(streaming_request):
                if event.type == StreamEventType.CONTENT_DELTA:
                    content = event.data.get("content", "")
                    full_response += content
                    yield event
                elif event.type == StreamEventType.FUNCTION_CALL_COMPLETE:
                    tool_calls.append(event.data)
                    yield event
                elif event.type == StreamEventType.COMPLETION:
                    # Create assistant message when complete
                    assistant_message_data = MessageCreate(
                        content=full_response,
                        role=MessageRole.ASSISTANT,
                        conversation_id=request.conversation_id,
                        metadata={
                            "tool_calls": tool_calls,
                            "streaming": True
                        }
                    )
                    await message_crud.create(db, obj_in=assistant_message_data)
                    yield event
                else:
                    yield event
        
        return stream_generator()
    
    async def get_conversation_history(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        limit: Optional[int] = None
    ) -> List[MessageResponse]:
        """
        Get conversation message history.
        
        Args:
            db: Database session
            conversation_id: Conversation ID
            limit: Optional limit on number of messages
            
        Returns:
            List of message responses
        """
        messages = await message_crud.get_by_conversation(
            db, conversation_id=conversation_id, limit=limit
        )
        return [MessageResponse.from_orm(msg) for msg in messages]
    
    async def update_agent_config(
        self,
        conversation_id: UUID,
        config_updates: Dict[str, Any]
    ) -> None:
        """
        Update agent configuration for conversation.
        
        Args:
            conversation_id: Conversation ID
            config_updates: Configuration updates
        """
        agent_key = str(conversation_id)
        
        if agent_key in self.active_agents:
            agent = self.active_agents[agent_key]
            
            # Update configuration
            for key, value in config_updates.items():
                if hasattr(agent.config, key):
                    setattr(agent.config, key, value)
            
            logger.info(f"Updated agent config for conversation {conversation_id}")
    
    async def clear_agent_memory(
        self,
        conversation_id: UUID
    ) -> None:
        """
        Clear agent memory for conversation.
        
        Args:
            conversation_id: Conversation ID
        """
        if conversation_id in self.memory_managers:
            memory_manager = self.memory_managers[conversation_id]
            await memory_manager.clear_all_memories()
            logger.info(f"Cleared memory for conversation {conversation_id}")
    
    async def get_agent_stats(
        self,
        conversation_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get agent statistics.
        
        Args:
            conversation_id: Optional specific conversation ID
            
        Returns:
            Agent statistics
        """
        if conversation_id:
            agent_key = str(conversation_id)
            if agent_key in self.active_agents:
                agent = self.active_agents[agent_key]
                memory_stats = {}
                if conversation_id in self.memory_managers:
                    memory_manager = self.memory_managers[conversation_id]
                    memory_stats = await memory_manager.get_memory_stats()
                
                return {
                    "agent_config": agent.config.__dict__,
                    "memory_stats": memory_stats,
                    "is_active": True
                }
            else:
                return {"is_active": False}
        else:
            # Global stats
            total_agents = len(self.active_agents)
            memory_stats = {}
            
            for conv_id, memory_manager in self.memory_managers.items():
                stats = await memory_manager.get_memory_stats()
                memory_stats[str(conv_id)] = stats
            
            return {
                "total_active_agents": total_agents,
                "active_conversations": list(self.active_agents.keys()),
                "memory_stats": memory_stats
            }
    
    async def cleanup_inactive_agents(
        self,
        max_idle_time: float = 3600.0  # 1 hour
    ) -> int:
        """
        Clean up inactive agents.
        
        Args:
            max_idle_time: Maximum idle time in seconds
            
        Returns:
            Number of agents cleaned up
        """
        import time
        current_time = time.time()
        cleanup_count = 0
        
        agents_to_remove = []
        for agent_key, agent in self.active_agents.items():
            # Check if agent has been idle
            if hasattr(agent, 'last_activity'):
                idle_time = current_time - agent.last_activity
                if idle_time > max_idle_time:
                    agents_to_remove.append(agent_key)
        
        # Remove inactive agents
        for agent_key in agents_to_remove:
            del self.active_agents[agent_key]
            cleanup_count += 1
            
            # Clean up associated memory
            try:
                conv_id = UUID(agent_key)
                if conv_id in self.memory_managers:
                    del self.memory_managers[conv_id]
            except ValueError:
                pass
        
        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} inactive agents")
        
        return cleanup_count


# Singleton instance
agent_service = AgentService()
