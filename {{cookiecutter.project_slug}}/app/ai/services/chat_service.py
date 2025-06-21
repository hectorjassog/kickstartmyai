"""Chat service for handling conversations."""

from typing import List, Optional, AsyncGenerator
from sqlalchemy.orm import Session

from app.ai.providers.factory import get_ai_provider
from app.ai.providers.base import ChatMessage
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.crud.message import message_crud
from app.schemas.message import MessageCreate
from app.core.unit_of_work import AIUnitOfWork, get_ai_unit_of_work


class ChatService:
    """Service for handling AI chat interactions."""
    
    def __init__(self, provider_name: str = "openai", model: Optional[str] = None):
        self.provider = get_ai_provider(provider_name, model=model)
    
    async def chat(
        self,
        conversation: Conversation,
        user_message: str,
        db: Optional[Session] = None,
        uow: Optional[AIUnitOfWork] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate chat response for a conversation."""
        # Use UoW if provided, otherwise create one
        if uow is None:
            async with get_ai_unit_of_work() as uow:
                return await self._chat_with_uow(
                    conversation, user_message, uow, temperature, max_tokens
                )
        else:
            return await self._chat_with_uow(
                conversation, user_message, uow, temperature, max_tokens
            )
    
    async def _chat_with_uow(
        self,
        conversation: Conversation,
        user_message: str,
        uow: AIUnitOfWork,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """Internal method for chat with UoW."""
        # Get conversation history
        messages = await self._get_conversation_messages(conversation, uow)
        
        # Add user message
        messages.append(ChatMessage(role="user", content=user_message))
        
        # Save user message to database
        user_msg_create = MessageCreate(
            content=user_message,
            role=MessageRole.USER,
            conversation_id=conversation.id
        )
        await uow.messages.create(obj_in=user_msg_create)
        
        # Generate AI response
        response = await self.provider.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Save AI response to database
        ai_msg_create = MessageCreate(
            content=response.content,
            role=MessageRole.ASSISTANT,
            conversation_id=conversation.id
        )
        await uow.messages.create(obj_in=ai_msg_create)
        
        return response.content
    
    async def stream_chat(
        self,
        conversation: Conversation,
        user_message: str,
        db: Optional[Session] = None,
        uow: Optional[AIUnitOfWork] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """Stream chat response for a conversation."""
        # Get conversation history
        messages = self._get_conversation_messages(conversation)
        
        # Add user message
        messages.append(ChatMessage(role="user", content=user_message))
        
        # Save user message to database
        user_msg_create = MessageCreate(
            content=user_message,
            role=MessageRole.USER,
            conversation_id=conversation.id
        )
        message_crud.create(db=db, obj_in=user_msg_create)
        
        # Collect full response for saving
        full_response = ""
        
        # Stream AI response
        async for chunk in self.provider.stream_chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        ):
            full_response += chunk
            yield chunk
        
        # Save complete AI response to database
        ai_msg_create = MessageCreate(
            content=full_response,
            role=MessageRole.ASSISTANT,
            conversation_id=conversation.id
        )
        message_crud.create(db=db, obj_in=ai_msg_create)
    
    async def _get_conversation_messages(self, conversation: Conversation, uow: AIUnitOfWork) -> List[ChatMessage]:
        """Convert conversation messages to ChatMessage format."""
        messages = []
        
        # Add system message if needed
        messages.append(ChatMessage(
            role="system",
            content="You are a helpful AI assistant."
        ))
        
        # Get conversation history from database through UoW
        conversation_messages = await uow.messages.get_conversation_messages(
            conversation_id=conversation.id, limit=50
        )
        
        # Add conversation history
        for message in conversation_messages:
            messages.append(ChatMessage(
                role=message.role.value,
                content=message.content
            ))
        
        return messages
