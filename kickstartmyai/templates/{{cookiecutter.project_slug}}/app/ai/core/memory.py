"""
Memory System - Manages different types of memory for AI agents including conversation history,
long-term memory, and context management.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Types of memory that can be managed."""
    CONVERSATION = "conversation"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    WORKING = "working"
    PROCEDURAL = "procedural"


class MemoryEntry(BaseModel):
    """Individual memory entry."""
    
    id: UUID = Field(default_factory=uuid4)
    type: MemoryType
    content: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    accessed_at: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = Field(default=0)
    
    # Memory-specific fields
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    decay_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    tags: List[str] = Field(default_factory=list)


class ConversationMemory(BaseModel):
    """Specific memory for conversation history."""
    
    conversation_id: UUID
    user_message: str
    assistant_response: str
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Analysis metadata
    sentiment: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    entities: List[Dict[str, Any]] = Field(default_factory=list)


class Memory:
    """
    Advanced memory system for AI agents with multiple memory types and persistence.
    """
    
    def __init__(
        self,
        max_entries_per_type: int = 1000,
        default_decay_rate: float = 0.1,
        auto_cleanup: bool = True,
        cleanup_interval_hours: int = 24
    ):
        """
        Initialize the memory system.
        
        Args:
            max_entries_per_type: Maximum entries per memory type
            default_decay_rate: Default decay rate for memories
            auto_cleanup: Whether to automatically clean up old memories
            cleanup_interval_hours: Hours between cleanup runs
        """
        self.max_entries_per_type = max_entries_per_type
        self.default_decay_rate = default_decay_rate
        self.auto_cleanup = auto_cleanup
        self.cleanup_interval_hours = cleanup_interval_hours
        
        # Memory storage
        self.memories: Dict[MemoryType, Dict[UUID, MemoryEntry]] = {
            memory_type: {} for memory_type in MemoryType
        }
        
        # Conversation-specific storage
        self.conversations: Dict[UUID, List[ConversationMemory]] = {}
        
        # Indexing for efficient retrieval
        self.tags_index: Dict[str, List[UUID]] = {}
        self.content_index: Dict[str, List[UUID]] = {}
        
        # Start cleanup task if enabled
        if auto_cleanup:
            asyncio.create_task(self._cleanup_task())
    
    async def store_memory(
        self,
        memory_type: MemoryType,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        tags: Optional[List[str]] = None
    ) -> UUID:
        """
        Store a memory entry.
        
        Args:
            memory_type: Type of memory to store
            content: Content of the memory
            metadata: Additional metadata
            importance: Importance score (0.0 to 1.0)
            tags: Tags for indexing
            
        Returns:
            UUID of the stored memory
        """
        memory = MemoryEntry(
            type=memory_type,
            content=content,
            metadata=metadata or {},
            importance=importance,
            decay_rate=self.default_decay_rate,
            tags=tags or []
        )
        
        # Store memory
        self.memories[memory_type][memory.id] = memory
        
        # Update indices
        await self._update_indices(memory)
        
        # Enforce size limits
        await self._enforce_size_limits(memory_type)
        
        return memory.id
    
    async def retrieve_memory(
        self,
        memory_id: UUID,
        update_access: bool = True
    ) -> Optional[MemoryEntry]:
        """
        Retrieve a specific memory by ID.
        
        Args:
            memory_id: ID of the memory to retrieve
            update_access: Whether to update access metadata
            
        Returns:
            Memory entry if found
        """
        for memory_type in MemoryType:
            memory = self.memories[memory_type].get(memory_id)
            if memory:
                if update_access:
                    memory.accessed_at = datetime.utcnow()
                    memory.access_count += 1
                return memory
        return None
    
    async def search_memories(
        self,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        content_query: Optional[str] = None,
        min_importance: float = 0.0,
        limit: int = 10,
        sort_by: str = "created_at"
    ) -> List[MemoryEntry]:
        """
        Search memories based on various criteria.
        
        Args:
            memory_type: Type of memory to search
            tags: Tags to match
            content_query: Content to search for
            min_importance: Minimum importance threshold
            limit: Maximum number of results
            sort_by: Field to sort by
            
        Returns:
            List of matching memories
        """
        results = []
        
        # Determine which memory types to search
        types_to_search = [memory_type] if memory_type else list(MemoryType)
        
        for mtype in types_to_search:
            for memory in self.memories[mtype].values():
                # Check importance threshold
                if memory.importance < min_importance:
                    continue
                
                # Check tags
                if tags and not any(tag in memory.tags for tag in tags):
                    continue
                
                # Check content query
                if content_query and not self._content_matches(memory, content_query):
                    continue
                
                results.append(memory)
        
        # Sort results
        if sort_by == "importance":
            results.sort(key=lambda m: m.importance, reverse=True)
        elif sort_by == "accessed_at":
            results.sort(key=lambda m: m.accessed_at, reverse=True)
        elif sort_by == "access_count":
            results.sort(key=lambda m: m.access_count, reverse=True)
        else:  # created_at
            results.sort(key=lambda m: m.created_at, reverse=True)
        
        return results[:limit]
    
    async def store_conversation(
        self,
        conversation_id: UUID,
        user_message: str,
        assistant_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store a conversation exchange.
        
        Args:
            conversation_id: ID of the conversation
            user_message: User's message
            assistant_response: Assistant's response
            metadata: Additional metadata
        """
        conversation_memory = ConversationMemory(
            conversation_id=conversation_id,
            user_message=user_message,
            assistant_response=assistant_response,
            context=metadata or {}
        )
        
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        
        self.conversations[conversation_id].append(conversation_memory)
        
        # Also store as general memory
        await self.store_memory(
            memory_type=MemoryType.CONVERSATION,
            content={
                "conversation_id": str(conversation_id),
                "user_message": user_message,
                "assistant_response": assistant_response
            },
            metadata=metadata,
            importance=0.7,  # Conversations are generally important
            tags=["conversation", str(conversation_id)]
        )
    
    async def get_conversation_history(
        self,
        conversation_id: UUID,
        limit: int = 10,
        include_context: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for a specific conversation.
        
        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of exchanges to return
            include_context: Whether to include context metadata
            
        Returns:
            List of conversation exchanges
        """
        if conversation_id not in self.conversations:
            return []
        
        conversations = self.conversations[conversation_id]
        recent_conversations = conversations[-limit:] if limit > 0 else conversations
        
        result = []
        for conv in recent_conversations:
            entry = {
                "user_message": conv.user_message,
                "assistant_response": conv.assistant_response,
                "timestamp": conv.timestamp.isoformat()
            }
            
            if include_context:
                entry["context"] = conv.context
                entry["sentiment"] = conv.sentiment
                entry["topics"] = conv.topics
                entry["entities"] = conv.entities
            
            result.append(entry)
        
        return result
    
    async def update_memory(
        self,
        memory_id: UUID,
        content: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance: Optional[float] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Update an existing memory entry.
        
        Args:
            memory_id: ID of the memory to update
            content: New content
            metadata: New metadata
            importance: New importance score
            tags: New tags
            
        Returns:
            True if memory was updated, False if not found
        """
        memory = await self.retrieve_memory(memory_id, update_access=False)
        if not memory:
            return False
        
        # Update fields
        if content is not None:
            memory.content = content
        if metadata is not None:
            memory.metadata.update(metadata)
        if importance is not None:
            memory.importance = importance
        if tags is not None:
            memory.tags = tags
        
        # Update indices
        await self._update_indices(memory)
        
        return True
    
    async def delete_memory(self, memory_id: UUID) -> bool:
        """
        Delete a memory entry.
        
        Args:
            memory_id: ID of the memory to delete
            
        Returns:
            True if memory was deleted, False if not found
        """
        for memory_type in MemoryType:
            if memory_id in self.memories[memory_type]:
                memory = self.memories[memory_type][memory_id]
                
                # Remove from indices
                await self._remove_from_indices(memory)
                
                # Delete memory
                del self.memories[memory_type][memory_id]
                return True
        
        return False
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory system."""
        stats = {}
        
        for memory_type in MemoryType:
            memories = self.memories[memory_type]
            if memories:
                avg_importance = sum(m.importance for m in memories.values()) / len(memories)
                avg_access_count = sum(m.access_count for m in memories.values()) / len(memories)
            else:
                avg_importance = 0
                avg_access_count = 0
            
            stats[memory_type.value] = {
                "count": len(memories),
                "avg_importance": avg_importance,
                "avg_access_count": avg_access_count
            }
        
        stats["conversations"] = {
            "total_conversations": len(self.conversations),
            "total_exchanges": sum(len(conv) for conv in self.conversations.values())
        }
        
        stats["indices"] = {
            "tags": len(self.tags_index),
            "content_terms": len(self.content_index)
        }
        
        return stats
    
    async def _update_indices(self, memory: MemoryEntry) -> None:
        """Update search indices for a memory."""
        # Update tags index
        for tag in memory.tags:
            if tag not in self.tags_index:
                self.tags_index[tag] = []
            if memory.id not in self.tags_index[tag]:
                self.tags_index[tag].append(memory.id)
        
        # Update content index (simple keyword-based)
        content_text = json.dumps(memory.content).lower()
        words = content_text.split()
        for word in words:
            if len(word) > 3:  # Only index meaningful words
                if word not in self.content_index:
                    self.content_index[word] = []
                if memory.id not in self.content_index[word]:
                    self.content_index[word].append(memory.id)
    
    async def _remove_from_indices(self, memory: MemoryEntry) -> None:
        """Remove a memory from search indices."""
        # Remove from tags index
        for tag in memory.tags:
            if tag in self.tags_index:
                self.tags_index[tag] = [
                    mid for mid in self.tags_index[tag] if mid != memory.id
                ]
                if not self.tags_index[tag]:
                    del self.tags_index[tag]
        
        # Remove from content index
        content_text = json.dumps(memory.content).lower()
        words = content_text.split()
        for word in words:
            if word in self.content_index:
                self.content_index[word] = [
                    mid for mid in self.content_index[word] if mid != memory.id
                ]
                if not self.content_index[word]:
                    del self.content_index[word]
    
    def _content_matches(self, memory: MemoryEntry, query: str) -> bool:
        """Check if memory content matches a query."""
        content_text = json.dumps(memory.content).lower()
        return query.lower() in content_text
    
    async def _enforce_size_limits(self, memory_type: MemoryType) -> None:
        """Enforce size limits for memory types."""
        memories = self.memories[memory_type]
        
        if len(memories) > self.max_entries_per_type:
            # Remove oldest, least important memories
            sorted_memories = sorted(
                memories.values(),
                key=lambda m: (m.importance, m.accessed_at)
            )
            
            to_remove = len(memories) - self.max_entries_per_type
            for memory in sorted_memories[:to_remove]:
                await self._remove_from_indices(memory)
                del memories[memory.id]
    
    async def _cleanup_task(self) -> None:
        """Background task for cleaning up old memories."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval_hours * 3600)
                await self._cleanup_memories()
            except Exception as e:
                print(f"Error in memory cleanup task: {e}")
    
    async def _cleanup_memories(self) -> None:
        """Clean up old and low-importance memories."""
        cutoff_time = datetime.utcnow() - timedelta(days=30)  # 30 days old
        
        for memory_type in MemoryType:
            memories = self.memories[memory_type]
            to_remove = []
            
            for memory_id, memory in memories.items():
                # Apply decay
                age_days = (datetime.utcnow() - memory.created_at).days
                decayed_importance = memory.importance * (1 - memory.decay_rate) ** age_days
                
                # Remove if very old and low importance
                if (memory.created_at < cutoff_time and 
                    decayed_importance < 0.1 and 
                    memory.access_count < 2):
                    to_remove.append(memory_id)
            
            # Remove memories
            for memory_id in to_remove:
                memory = memories[memory_id]
                await self._remove_from_indices(memory)
                del memories[memory_id]
