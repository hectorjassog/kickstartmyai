"""Streaming service for real-time AI responses."""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional
from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime

from pydantic import BaseModel, Field

from app.ai.providers.factory import get_ai_provider
from app.ai.providers.base import ChatMessage

logger = logging.getLogger(__name__)


class StreamEventType(str, Enum):
    """Types of streaming events."""
    START = "start"
    CHUNK = "chunk"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    END = "end"
    ERROR = "error"


class StreamingRequest(BaseModel):
    """Request for streaming chat."""
    conversation_id: Optional[UUID] = None
    message: str = Field(..., description="User message")
    agent_id: Optional[UUID] = None
    provider: str = Field(default="openai", description="AI provider to use")
    model: str = Field(default="gpt-4", description="Model to use")
    temperature: float = Field(default=0.7, description="Temperature for responses")
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens to generate")
    tools: Optional[List[Dict[str, Any]]] = Field(default=None, description="Available tools")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class StreamEvent(BaseModel):
    """Streaming event."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: StreamEventType
    data: Any = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StreamingService:
    """Service for handling streaming AI responses."""
    
    def __init__(self):
        """Initialize the streaming service."""
        self.active_streams: Dict[str, Dict[str, Any]] = {}
    
    async def stream_chat(
        self,
        request: StreamingRequest
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream chat responses.
        
        Args:
            request: Streaming request
            
        Yields:
            Stream events
        """
        stream_id = str(uuid4())
        
        try:
            # Initialize stream
            self.active_streams[stream_id] = {
                "request": request,
                "started_at": datetime.utcnow(),
                "status": "active"
            }
            
            # Send start event
            yield StreamEvent(
                type=StreamEventType.START,
                data={
                    "stream_id": stream_id,
                    "conversation_id": str(request.conversation_id) if request.conversation_id else None,
                    "agent_id": str(request.agent_id) if request.agent_id else None
                },
                metadata={"provider": request.provider, "model": request.model}
            )
            
            # Get AI provider
            provider = get_ai_provider(request.provider, model=request.model)
            
            # Prepare messages
            messages = self._prepare_messages(request)
            
            # Stream response
            full_response = ""
            
            async for chunk in provider.stream_chat_completion(
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                tools=request.tools
            ):
                if chunk:
                    full_response += chunk
                    
                    # Send chunk event
                    yield StreamEvent(
                        type=StreamEventType.CHUNK,
                        data={"content": chunk},
                        metadata={
                            "stream_id": stream_id,
                            "total_length": len(full_response)
                        }
                    )
            
            # Send end event
            yield StreamEvent(
                type=StreamEventType.END,
                data={
                    "content": full_response,
                    "finished": True
                },
                metadata={
                    "stream_id": stream_id,
                    "total_chunks": len(full_response.split()),
                    "final_length": len(full_response)
                }
            )
            
        except Exception as e:
            logger.error(f"Streaming error for stream {stream_id}: {e}")
            
            # Send error event
            yield StreamEvent(
                type=StreamEventType.ERROR,
                data={"error": str(e)},
                metadata={"stream_id": stream_id}
            )
            
        finally:
            # Clean up stream
            if stream_id in self.active_streams:
                self.active_streams[stream_id]["status"] = "completed"
                # Remove after some time to allow for debugging
                asyncio.create_task(self._cleanup_stream(stream_id, delay=300))  # 5 minutes
    
    async def stream_with_tools(
        self,
        request: StreamingRequest,
        tool_executor: Optional[Any] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream chat responses with tool execution support.
        
        Args:
            request: Streaming request
            tool_executor: Tool executor for function calls
            
        Yields:
            Stream events
        """
        stream_id = str(uuid4())
        
        try:
            # Send start event
            yield StreamEvent(
                type=StreamEventType.START,
                data={"stream_id": stream_id, "supports_tools": True},
                metadata={"provider": request.provider, "model": request.model}
            )
            
            # Get AI provider
            provider = get_ai_provider(request.provider, model=request.model)
            
            # Prepare messages
            messages = self._prepare_messages(request)
            
            # Get response with potential tool calls
            response = await provider.chat_completion(
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                tools=request.tools
            )
            
            # Stream the content
            if response.content:
                for chunk in response.content.split():
                    yield StreamEvent(
                        type=StreamEventType.CHUNK,
                        data={"content": chunk + " "},
                        metadata={"stream_id": stream_id}
                    )
                    
                    # Small delay for realistic streaming
                    await asyncio.sleep(0.01)
            
            # Handle tool calls if present
            if response.tool_calls and tool_executor:
                for tool_call in response.tool_calls:
                    # Send tool call event
                    yield StreamEvent(
                        type=StreamEventType.TOOL_CALL,
                        data={
                            "tool_name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                            "call_id": tool_call.id
                        },
                        metadata={"stream_id": stream_id}
                    )
                    
                    # Execute tool
                    try:
                        tool_result = await tool_executor.execute_tool(
                            tool_name=tool_call.function.name,
                            arguments=json.loads(tool_call.function.arguments),
                            context=request.context
                        )
                        
                        # Send tool result event
                        yield StreamEvent(
                            type=StreamEventType.TOOL_RESULT,
                            data={
                                "tool_name": tool_call.function.name,
                                "result": tool_result.result,
                                "success": tool_result.success,
                                "call_id": tool_call.id
                            },
                            metadata={"stream_id": stream_id}
                        )
                        
                    except Exception as e:
                        # Send tool error event
                        yield StreamEvent(
                            type=StreamEventType.TOOL_RESULT,
                            data={
                                "tool_name": tool_call.function.name,
                                "error": str(e),
                                "success": False,
                                "call_id": tool_call.id
                            },
                            metadata={"stream_id": stream_id}
                        )
            
            # Send end event
            yield StreamEvent(
                type=StreamEventType.END,
                data={"finished": True},
                metadata={"stream_id": stream_id}
            )
            
        except Exception as e:
            logger.error(f"Tool streaming error for stream {stream_id}: {e}")
            
            yield StreamEvent(
                type=StreamEventType.ERROR,
                data={"error": str(e)},
                metadata={"stream_id": stream_id}
            )
    
    def _prepare_messages(self, request: StreamingRequest) -> List[ChatMessage]:
        """Prepare messages for AI provider."""
        messages = []
        
        # Add system message if available in context
        if "system_prompt" in request.context:
            messages.append(ChatMessage(
                role="system",
                content=request.context["system_prompt"]
            ))
        
        # Add conversation history if available in context
        if "history" in request.context:
            for msg in request.context["history"]:
                messages.append(ChatMessage(
                    role=msg.get("role", "user"),
                    content=msg.get("content", "")
                ))
        
        # Add current user message
        messages.append(ChatMessage(
            role="user",
            content=request.message
        ))
        
        return messages
    
    async def _cleanup_stream(self, stream_id: str, delay: int = 300):
        """Clean up stream data after delay."""
        await asyncio.sleep(delay)
        if stream_id in self.active_streams:
            del self.active_streams[stream_id]
            logger.debug(f"Cleaned up stream {stream_id}")
    
    def get_active_streams(self) -> List[Dict[str, Any]]:
        """Get information about active streams."""
        return [
            {
                "stream_id": stream_id,
                "started_at": info["started_at"].isoformat(),
                "status": info["status"],
                "conversation_id": str(info["request"].conversation_id) if info["request"].conversation_id else None
            }
            for stream_id, info in self.active_streams.items()
        ]
    
    def get_stream_info(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific stream."""
        if stream_id in self.active_streams:
            info = self.active_streams[stream_id]
            return {
                "stream_id": stream_id,
                "started_at": info["started_at"].isoformat(),
                "status": info["status"],
                "request": info["request"].dict()
            }
        return None


# Global instance
streaming_service = StreamingService() 