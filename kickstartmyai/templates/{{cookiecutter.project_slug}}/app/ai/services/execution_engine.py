"""
Agent Execution Engine

Core engine for orchestrating AI agent execution with provider integration,
tool calling, state management, and comprehensive error handling.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, AsyncGenerator, Union
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.ai.providers.factory import get_ai_provider
from app.ai.providers.base import BaseAIProvider, ChatMessage, ChatResponse
from app.ai.tools.manager import tool_manager, ToolExecutionContext, FunctionCall
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.models.execution import Execution, ExecutionStatus
from app.crud.execution import execution_crud
from app.crud.message import message_crud
from app.schemas.execution import ExecutionCreate, ExecutionUpdate
from app.schemas.message import MessageCreate
from app.core.config import settings

logger = logging.getLogger(__name__)


class ExecutionContext(BaseModel):
    """Context for agent execution."""
    agent_id: uuid.UUID
    conversation_id: uuid.UUID
    user_id: uuid.UUID
    execution_id: Optional[uuid.UUID] = None
    provider_name: str
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    tools_enabled: bool = True
    streaming: bool = False
    metadata: Dict[str, Any] = {}


class ExecutionResult(BaseModel):
    """Result of agent execution."""
    execution_id: uuid.UUID
    status: ExecutionStatus
    response: Optional[str] = None
    error: Optional[str] = None
    tokens_used: Optional[int] = None
    cost: Optional[Decimal] = None
    duration: Optional[float] = None
    tool_calls: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}


class AgentExecutionEngine:
    """
    Core engine for agent execution with AI provider integration.
    
    Handles:
    - AI provider orchestration
    - Tool integration and function calling
    - Execution state management
    - Error handling and recovery
    - Performance monitoring
    - Cost tracking
    """
    
    def __init__(self):
        self.active_executions: Dict[uuid.UUID, ExecutionContext] = {}
        self.provider_cache: Dict[str, BaseAIProvider] = {}
        self.max_function_calls = settings.MAX_FUNCTION_CALLS or 5
    
    async def execute_agent(
        self,
        agent: Agent,
        conversation: Conversation,
        user_message: str,
        db: AsyncSession,
        context: Optional[ExecutionContext] = None
    ) -> ExecutionResult:
        """
        Execute an agent with the given message.
        
        Args:
            agent: Agent to execute
            conversation: Conversation context
            user_message: User's input message
            db: Database session
            context: Optional execution context
            
        Returns:
            Execution result with response and metadata
        """
        # Create execution context
        if not context:
            context = ExecutionContext(
                agent_id=agent.id,
                conversation_id=conversation.id,
                user_id=conversation.user_id,
                provider_name=agent.provider,
                model=agent.model,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens,
                tools_enabled=settings.TOOLS_ENABLED and agent.tools_enabled
            )
        
        # Create execution record
        execution_create = ExecutionCreate(
            agent_id=agent.id,
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            status=ExecutionStatus.RUNNING,
            provider=context.provider_name,
            model=context.model,
            input_data={"user_message": user_message},
            metadata=context.metadata
        )
        
        execution = await execution_crud.create(db, obj_in=execution_create)
        context.execution_id = execution.id
        
        # Track active execution
        self.active_executions[execution.id] = context
        
        start_time = time.time()
        
        try:
            # Execute the agent with tool support
            result = await self._execute_with_tools(
                agent=agent,
                conversation=conversation,
                user_message=user_message,
                context=context,
                db=db
            )
            
            # Calculate execution metrics
            duration = time.time() - start_time
            
            # Update execution record
            execution_update = ExecutionUpdate(
                status=ExecutionStatus.COMPLETED,
                output_data={
                    "response": result.response,
                    "tool_calls": result.tool_calls
                },
                tokens_used=result.tokens_used,
                cost=result.cost,
                duration=duration,
                completed_at=datetime.utcnow(),
                metadata={**context.metadata, **result.metadata}
            )
            
            await execution_crud.update(db, db_obj=execution, obj_in=execution_update)
            
            return ExecutionResult(
                execution_id=execution.id,
                status=ExecutionStatus.COMPLETED,
                response=result.response,
                tokens_used=result.tokens_used,
                cost=result.cost,
                duration=duration,
                tool_calls=result.tool_calls,
                metadata=result.metadata
            )
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            
            # Update execution with error
            execution_update = ExecutionUpdate(
                status=ExecutionStatus.FAILED,
                error_message=str(e),
                error_type=type(e).__name__,
                stack_trace=str(e),
                completed_at=datetime.utcnow(),
                duration=time.time() - start_time
            )
            
            await execution_crud.update(db, db_obj=execution, obj_in=execution_update)
            
            return ExecutionResult(
                execution_id=execution.id,
                status=ExecutionStatus.FAILED,
                error=str(e),
                duration=time.time() - start_time
            )
            
        finally:
            # Clean up active execution
            self.active_executions.pop(execution.id, None)
    
    async def stream_agent_execution(
        self,
        agent: Agent,
        conversation: Conversation,
        user_message: str,
        db: AsyncSession,
        context: Optional[ExecutionContext] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream agent execution with real-time response.
        
        Args:
            agent: Agent to execute
            conversation: Conversation context
            user_message: User's input message
            db: Database session
            context: Optional execution context
            
        Yields:
            Response chunks as they are generated
        """
        # Create execution context
        if not context:
            context = ExecutionContext(
                agent_id=agent.id,
                conversation_id=conversation.id,
                user_id=conversation.user_id,
                provider_name=agent.provider,
                model=agent.model,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens,
                streaming=True,
                tools_enabled=settings.TOOLS_ENABLED and agent.tools_enabled
            )
        
        # Create execution record
        execution_create = ExecutionCreate(
            agent_id=agent.id,
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            status=ExecutionStatus.RUNNING,
            provider=context.provider_name,
            model=context.model,
            input_data={"user_message": user_message},
            metadata=context.metadata
        )
        
        execution = await execution_crud.create(db, obj_in=execution_create)
        context.execution_id = execution.id
        
        # Track active execution
        self.active_executions[execution.id] = context
        
        start_time = time.time()
        full_response = ""
        tool_calls_made = []
        
        try:
            # Get AI provider
            provider = await self._get_provider(context.provider_name, context.model)
            
            # Prepare messages
            messages = await self._prepare_messages(agent, conversation, user_message, db)
            
            # Save user message
            await self._save_user_message(user_message, conversation.id, db)
            
            # Add function schemas if tools are enabled
            function_schemas = None
            if context.tools_enabled:
                function_schemas = tool_manager.get_function_schemas()
            
            # Stream response with potential function calling
            async for chunk in provider.stream_chat_completion(
                messages=messages,
                temperature=context.temperature,
                max_tokens=context.max_tokens,
                functions=function_schemas
            ):
                full_response += chunk
                yield chunk
            
            # Check for function calls in the response
            # Note: This is simplified - in practice, you'd parse the response for function calls
            # and handle them appropriately based on the provider's format
            
            # Save assistant response
            await self._save_assistant_message(full_response, conversation.id, db)
            
            # Update execution record
            duration = time.time() - start_time
            execution_update = ExecutionUpdate(
                status=ExecutionStatus.COMPLETED,
                output_data={
                    "response": full_response,
                    "tool_calls": tool_calls_made
                },
                duration=duration,
                completed_at=datetime.utcnow()
            )
            
            await execution_crud.update(db, db_obj=execution, obj_in=execution_update)
            
        except Exception as e:
            logger.error(f"Streaming execution failed: {e}", exc_info=True)
            
            # Update execution with error
            execution_update = ExecutionUpdate(
                status=ExecutionStatus.FAILED,
                error_message=str(e),
                error_type=type(e).__name__,
                completed_at=datetime.utcnow(),
                duration=time.time() - start_time
            )
            
            await execution_crud.update(db, db_obj=execution, obj_in=execution_update)
            
            yield f"\n\n[Error: {str(e)}]"
            
        finally:
            # Clean up active execution
            self.active_executions.pop(execution.id, None)
    
    async def _execute_with_tools(
        self,
        agent: Agent,
        conversation: Conversation,
        user_message: str,
        context: ExecutionContext,
        db: AsyncSession
    ) -> ExecutionResult:
        """Execute agent with tool support and function calling."""
        # Get AI provider
        provider = await self._get_provider(context.provider_name, context.model)
        
        # Prepare messages
        messages = await self._prepare_messages(agent, conversation, user_message, db)
        
        # Save user message
        await self._save_user_message(user_message, conversation.id, db)
        
        # Prepare function schemas if tools are enabled
        function_schemas = None
        if context.tools_enabled:
            function_schemas = tool_manager.get_function_schemas()
        
        # Execute with function calling loop
        total_tokens = 0
        total_cost = Decimal("0")
        tool_calls_made = []
        function_call_count = 0
        
        while function_call_count < self.max_function_calls:
            # Generate response
            response = await provider.chat_completion(
                messages=messages,
                temperature=context.temperature,
                max_tokens=context.max_tokens,
                functions=function_schemas
            )
            
            # Accumulate usage
            if response.usage:
                total_tokens += response.usage.get("total_tokens", 0)
                total_cost += self._calculate_cost(response.usage, context.provider_name) or Decimal("0")
            
            # Check for function calls (simplified - depends on provider format)
            function_calls = self._extract_function_calls(response, context.provider_name)
            
            if not function_calls:
                # No function calls, we're done
                await self._save_assistant_message(response.content, conversation.id, db)
                break
            
            # Execute function calls
            tool_execution_context = ToolExecutionContext(
                execution_id=context.execution_id,
                user_id=context.user_id,
                agent_id=context.agent_id,
                conversation_id=context.conversation_id
            )
            
            function_results = await tool_manager.execute_function_calls(
                function_calls, tool_execution_context
            )
            
            # Record tool calls
            for call, result in function_results:
                tool_calls_made.append({
                    "function_name": call.name,
                    "arguments": call.arguments,
                    "result": result.to_dict(),
                    "call_id": call.call_id
                })
            
            # Add function results to conversation
            if context.provider_name == "openai":
                # Add assistant message with function calls
                messages.append(ChatMessage(
                    role="assistant",
                    content=response.content or "",
                    function_call=function_calls[0].to_dict() if function_calls else None
                ))
                
                # Add function results
                for call, result in function_results:
                    messages.append(ChatMessage(
                        role="function",
                        content=result.result if result.success else result.error,
                        name=call.name
                    ))
            
            function_call_count += 1
        
        # If we hit the max function calls, add a final response
        if function_call_count >= self.max_function_calls:
            final_response = await provider.chat_completion(
                messages=messages,
                temperature=context.temperature,
                max_tokens=context.max_tokens
            )
            await self._save_assistant_message(final_response.content, conversation.id, db)
            response = final_response
        
        return ExecutionResult(
            execution_id=context.execution_id,
            status=ExecutionStatus.COMPLETED,
            response=response.content,
            tokens_used=total_tokens,
            cost=total_cost,
            tool_calls=tool_calls_made,
            metadata={"model": response.model, "function_calls": function_call_count}
        )
    
    def _extract_function_calls(
        self,
        response: ChatResponse,
        provider_name: str
    ) -> List[FunctionCall]:
        """Extract function calls from AI provider response."""
        # This is a simplified implementation
        # In practice, you'd parse the actual response format from each provider
        
        function_calls = []
        
        # Check for function call indicators in response content
        # This would be replaced with proper parsing logic for each provider
        if response.content and "function_call:" in response.content.lower():
            # Mock function call extraction for demo
            # In reality, you'd parse the provider's specific function call format
            pass
        
        return function_calls
    
    async def _get_provider(self, provider_name: str, model: Optional[str] = None) -> BaseAIProvider:
        """Get AI provider with caching."""
        cache_key = f"{provider_name}:{model or 'default'}"
        
        if cache_key not in self.provider_cache:
            self.provider_cache[cache_key] = get_ai_provider(provider_name, model=model)
        
        return self.provider_cache[cache_key]
    
    async def _prepare_messages(
        self,
        agent: Agent,
        conversation: Conversation,
        user_message: str,
        db: AsyncSession
    ) -> List[ChatMessage]:
        """Prepare messages for AI provider."""
        messages = []
        
        # Add system prompt
        system_prompt = agent.system_prompt or "You are a helpful AI assistant."
        
        # Add tool information to system prompt if tools are enabled
        if settings.TOOLS_ENABLED and agent.tools_enabled:
            available_tools = tool_manager.get_available_tools()
            if available_tools:
                tool_descriptions = [
                    f"- {tool.name}: {tool.description}"
                    for tool in available_tools
                ]
                system_prompt += f"\n\nYou have access to the following tools:\n" + "\n".join(tool_descriptions)
        
        messages.append(ChatMessage(role="system", content=system_prompt))
        
        # Add conversation history (last N messages)
        history_limit = 20  # Configurable
        recent_messages = await message_crud.get_conversation_messages(
            db, conversation_id=conversation.id, limit=history_limit
        )
        
        for msg in recent_messages:
            messages.append(ChatMessage(
                role=msg.role.value,
                content=msg.content
            ))
        
        # Add current user message
        messages.append(ChatMessage(role="user", content=user_message))
        
        return messages
    
    async def _save_user_message(
        self,
        content: str,
        conversation_id: uuid.UUID,
        db: AsyncSession
    ) -> Message:
        """Save user message to database."""
        message_create = MessageCreate(
            content=content,
            role=MessageRole.USER,
            conversation_id=conversation_id
        )
        return await message_crud.create(db, obj_in=message_create)
    
    async def _save_assistant_message(
        self,
        content: str,
        conversation_id: uuid.UUID,
        db: AsyncSession
    ) -> Message:
        """Save assistant message to database."""
        message_create = MessageCreate(
            content=content,
            role=MessageRole.ASSISTANT,
            conversation_id=conversation_id
        )
        return await message_crud.create(db, obj_in=message_create)
    
    def _calculate_cost(
        self,
        usage: Optional[Dict[str, int]],
        provider_name: str
    ) -> Optional[Decimal]:
        """Calculate execution cost based on usage."""
        if not usage or not usage.get("total_tokens"):
            return None
        
        # Simplified cost calculation (should be configurable)
        cost_per_1k_tokens = {
            "openai": Decimal("0.002"),
            "anthropic": Decimal("0.003"),
            "gemini": Decimal("0.001")
        }
        
        rate = cost_per_1k_tokens.get(provider_name, Decimal("0.002"))
        total_tokens = usage["total_tokens"]
        
        return (Decimal(total_tokens) / 1000) * rate
    
    async def cancel_execution(self, execution_id: uuid.UUID, db: AsyncSession) -> bool:
        """Cancel an active execution."""
        if execution_id not in self.active_executions:
            return False
        
        # Update execution status
        execution = await execution_crud.get(db, id=execution_id)
        if execution:
            execution_update = ExecutionUpdate(
                status=ExecutionStatus.CANCELLED,
                completed_at=datetime.utcnow(),
                error_message="Execution cancelled by user"
            )
            await execution_crud.update(db, db_obj=execution, obj_in=execution_update)
        
        # Remove from active executions
        self.active_executions.pop(execution_id, None)
        
        return True
    
    async def get_execution_status(self, execution_id: uuid.UUID) -> Optional[ExecutionContext]:
        """Get status of an active execution."""
        return self.active_executions.get(execution_id)
    
    async def list_active_executions(self) -> List[ExecutionContext]:
        """List all active executions."""
        return list(self.active_executions.values())
    
    async def cleanup_stale_executions(self, db: AsyncSession, max_age_hours: int = 24):
        """Clean up stale executions that are still marked as running."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        # Find stale executions
        stale_executions = await execution_crud.get_stale_executions(db, cutoff_time)
        
        for execution in stale_executions:
            execution_update = ExecutionUpdate(
                status=ExecutionStatus.FAILED,
                error_message="Execution timed out",
                completed_at=datetime.utcnow()
            )
            await execution_crud.update(db, db_obj=execution, obj_in=execution_update)
            
            # Remove from active executions if present
            self.active_executions.pop(execution.id, None)
        
        logger.info(f"Cleaned up {len(stale_executions)} stale executions")


# Global execution engine instance
execution_engine = AgentExecutionEngine() 