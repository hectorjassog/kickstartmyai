"""
AI Agent - Core agent class for orchestrating AI workflows and tool usage.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Type, Union
from uuid import UUID, uuid4
from datetime import datetime

from pydantic import BaseModel, Field

from .memory import Memory, MemoryType
from .executor import ToolExecutor
from .orchestrator import WorkflowOrchestrator
from ..providers.base import BaseAIProvider, ChatMessage, MessageRole
from ..tools.base import BaseTool


class AgentConfig(BaseModel):
    """Configuration for an AI agent."""
    
    name: str = Field(..., description="Name of the agent")
    description: str = Field(..., description="Description of the agent's purpose")
    system_prompt: str = Field(..., description="System prompt for the agent")
    provider: str = Field(default="openai", description="AI provider to use")
    model: str = Field(default="gpt-4", description="Model to use")
    temperature: float = Field(default=0.7, description="Temperature for responses")
    max_tokens: int = Field(default=2000, description="Maximum tokens to generate")
    max_iterations: int = Field(default=10, description="Maximum iterations for tool usage")
    enable_memory: bool = Field(default=True, description="Whether to use memory")
    memory_types: List[MemoryType] = Field(default=[MemoryType.CONVERSATION], description="Types of memory to use")


class AgentState(BaseModel):
    """Current state of an AI agent."""
    
    agent_id: UUID
    conversation_id: Optional[UUID] = None
    current_iteration: int = 0
    is_active: bool = False
    last_action: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AgentResponse(BaseModel):
    """Response from an AI agent."""
    
    content: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tokens_used: int = 0
    finish_reason: str = "stop"


class AIAgent:
    """
    AI Agent that can use tools, maintain memory, and execute complex workflows.
    """
    
    def __init__(
        self,
        config: AgentConfig,
        ai_provider: BaseAIProvider,
        tools: Optional[List[BaseTool]] = None,
        memory: Optional[Memory] = None,
        executor: Optional[ToolExecutor] = None,
        orchestrator: Optional[WorkflowOrchestrator] = None
    ):
        """
        Initialize the AI agent.
        
        Args:
            config: Agent configuration
            ai_provider: AI provider instance
            tools: List of available tools
            memory: Memory system instance
            executor: Tool executor instance
            orchestrator: Workflow orchestrator instance
        """
        self.config = config
        self.ai_provider = ai_provider
        self.tools = tools or []
        self.memory = memory
        self.executor = executor or ToolExecutor(tools=self.tools)
        self.orchestrator = orchestrator or WorkflowOrchestrator()
        
        # Agent state
        self.agent_id = uuid4()
        self.state = AgentState(agent_id=self.agent_id)
        
        # Tool registry
        self.tool_registry = {tool.name: tool for tool in self.tools}
    
    async def chat(
        self,
        message: str,
        conversation_id: Optional[UUID] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Process a chat message and return a response.
        
        Args:
            message: User message
            conversation_id: Optional conversation ID for memory
            context: Additional context for the conversation
            
        Returns:
            Agent response
        """
        try:
            self.state.is_active = True
            self.state.conversation_id = conversation_id
            self.state.current_iteration = 0
            
            if context:
                self.state.context.update(context)
            
            # Load conversation history from memory
            messages = await self._load_conversation_history(conversation_id)
            
            # Add user message
            messages.append(ChatMessage(
                role=MessageRole.USER,
                content=message
            ))
            
            # Process the conversation
            response = await self._process_conversation(messages)
            
            # Store conversation in memory
            if self.memory and conversation_id:
                await self._store_conversation(conversation_id, message, response.content)
            
            return response
            
        finally:
            self.state.is_active = False
            self.state.updated_at = datetime.utcnow()
    
    async def execute_workflow(
        self,
        workflow_name: str,
        inputs: Dict[str, Any],
        conversation_id: Optional[UUID] = None
    ) -> AgentResponse:
        """
        Execute a predefined workflow.
        
        Args:
            workflow_name: Name of the workflow to execute
            inputs: Input parameters for the workflow
            conversation_id: Optional conversation ID for memory
            
        Returns:
            Agent response
        """
        try:
            self.state.is_active = True
            self.state.conversation_id = conversation_id
            
            # Execute workflow through orchestrator
            result = await self.orchestrator.execute_workflow(
                workflow_name=workflow_name,
                inputs=inputs,
                agent=self,
                context=self.state.context
            )
            
            return AgentResponse(
                content=result.get("output", "Workflow completed successfully"),
                metadata={
                    "workflow_name": workflow_name,
                    "execution_time": result.get("execution_time"),
                    "steps_executed": result.get("steps_executed")
                }
            )
            
        finally:
            self.state.is_active = False
            self.state.updated_at = datetime.utcnow()
    
    async def add_tool(self, tool: BaseTool) -> None:
        """Add a tool to the agent's toolkit."""
        self.tools.append(tool)
        self.tool_registry[tool.name] = tool
        await self.executor.add_tool(tool)
    
    async def remove_tool(self, tool_name: str) -> None:
        """Remove a tool from the agent's toolkit."""
        if tool_name in self.tool_registry:
            tool = self.tool_registry.pop(tool_name)
            self.tools.remove(tool)
            await self.executor.remove_tool(tool_name)
    
    async def _process_conversation(self, messages: List[ChatMessage]) -> AgentResponse:
        """Process a conversation with potential tool usage."""
        current_messages = messages.copy()
        tool_calls = []
        total_tokens = 0
        
        # Add system prompt
        system_message = ChatMessage(
            role=MessageRole.SYSTEM,
            content=self._build_system_prompt()
        )
        current_messages.insert(0, system_message)
        
        for iteration in range(self.config.max_iterations):
            self.state.current_iteration = iteration
            
            # Get AI response
            response = await self.ai_provider.chat_completion(
                messages=current_messages,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                tools=self._get_tool_schemas() if self.tools else None
            )
            
            total_tokens += response.usage.total_tokens if response.usage else 0
            
            # Add assistant response to conversation
            current_messages.append(ChatMessage(
                role=MessageRole.ASSISTANT,
                content=response.content or "",
                tool_calls=response.tool_calls
            ))
            
            # Check if AI wants to use tools
            if response.tool_calls:
                # Execute tool calls
                for tool_call in response.tool_calls:
                    try:
                        tool_result = await self.executor.execute_tool(
                            tool_name=tool_call.function.name,
                            arguments=json.loads(tool_call.function.arguments),
                            context=self.state.context
                        )
                        
                        # Add tool result to conversation
                        current_messages.append(ChatMessage(
                            role=MessageRole.TOOL,
                            content=json.dumps(tool_result.result),
                            tool_call_id=tool_call.id
                        ))
                        
                        tool_calls.append({
                            "tool": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                            "result": tool_result.result
                        })
                        
                        self.state.last_action = f"Used tool: {tool_call.function.name}"
                        
                    except Exception as e:
                        # Add error to conversation
                        current_messages.append(ChatMessage(
                            role=MessageRole.TOOL,
                            content=f"Error executing tool: {str(e)}",
                            tool_call_id=tool_call.id
                        ))
                
                # Continue conversation after tool usage
                continue
            else:
                # No more tool calls, return final response
                return AgentResponse(
                    content=response.content or "",
                    tool_calls=tool_calls,
                    tokens_used=total_tokens,
                    finish_reason=response.finish_reason or "stop"
                )
        
        # Max iterations reached
        return AgentResponse(
            content=current_messages[-1].content or "Maximum iterations reached",
            tool_calls=tool_calls,
            tokens_used=total_tokens,
            finish_reason="max_iterations",
            metadata={"warning": "Maximum iterations reached"}
        )
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the agent."""
        base_prompt = self.config.system_prompt
        
        if self.tools:
            tool_descriptions = "\n".join([
                f"- {tool.name}: {tool.description}"
                for tool in self.tools
            ])
            base_prompt += f"\n\nAvailable tools:\n{tool_descriptions}"
            base_prompt += "\n\nUse tools when necessary to accomplish tasks. Always explain your reasoning."
        
        return base_prompt
    
    def _get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get tool schemas for the AI provider."""
        return [tool.get_schema() for tool in self.tools]
    
    async def _load_conversation_history(
        self,
        conversation_id: Optional[UUID]
    ) -> List[ChatMessage]:
        """Load conversation history from memory."""
        if not self.memory or not conversation_id:
            return []
        
        try:
            history = await self.memory.get_conversation_history(
                conversation_id=conversation_id,
                limit=10  # Limit to recent messages
            )
            
            messages = []
            for entry in history:
                messages.append(ChatMessage(
                    role=MessageRole.USER,
                    content=entry.get("user_message", "")
                ))
                if entry.get("assistant_response"):
                    messages.append(ChatMessage(
                        role=MessageRole.ASSISTANT,
                        content=entry["assistant_response"]
                    ))
            
            return messages
            
        except Exception as e:
            # Log error but continue without history
            print(f"Error loading conversation history: {e}")
            return []
    
    async def _store_conversation(
        self,
        conversation_id: UUID,
        user_message: str,
        assistant_response: str
    ) -> None:
        """Store conversation in memory."""
        if not self.memory:
            return
        
        try:
            await self.memory.store_conversation(
                conversation_id=conversation_id,
                user_message=user_message,
                assistant_response=assistant_response,
                metadata={
                    "agent_id": str(self.agent_id),
                    "agent_name": self.config.name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            # Log error but continue
            print(f"Error storing conversation: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "agent_id": str(self.agent_id),
            "name": self.config.name,
            "is_active": self.state.is_active,
            "current_iteration": self.state.current_iteration,
            "conversation_id": str(self.state.conversation_id) if self.state.conversation_id else None,
            "last_action": self.state.last_action,
            "tools_available": len(self.tools),
            "memory_enabled": self.memory is not None,
            "created_at": self.state.created_at.isoformat(),
            "updated_at": self.state.updated_at.isoformat()
        }
