"""
Base CRUD operations for all models.

This module provides a generic base class for CRUD operations
that can be extended by specific model CRUD classes.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base


ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base CRUD class with common async operations."""
    
    def __init__(self, model: Type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).
        
        Args:
            model: A SQLAlchemy model class
        """
        self.model = model

    async def get(self, db: AsyncSession, id: Union[UUID, str, int]) -> Optional[ModelType]:
        """Get a single record by ID."""
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records with pagination."""
        result = await db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """Update an existing record."""
        obj_data = jsonable_encoder(db_obj)
        
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        # Update timestamp if model has updated_at field
        if hasattr(db_obj, 'updated_at'):
            db_obj.updated_at = datetime.utcnow()
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: Union[UUID, str, int]) -> Optional[ModelType]:
        """Delete a record by ID."""
        result = await db.execute(select(self.model).where(self.model.id == id))
        obj = result.scalar_one_or_none()
        
        if obj:
            await db.delete(obj)
            await db.commit()
        
        return obj

    async def count(self, db: AsyncSession) -> int:
        """Count total number of records."""
        result = await db.execute(select(func.count(self.model.id)))
        return result.scalar()

    async def exists(self, db: AsyncSession, *, id: Union[UUID, str, int]) -> bool:
        """Check if a record exists by ID."""
        result = await db.execute(
            select(func.count(self.model.id)).where(self.model.id == id)
        )
        return result.scalar() > 0

    async def get_or_create(
        self,
        db: AsyncSession,
        *,
        defaults: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> tuple[ModelType, bool]:
        """Get an existing record or create a new one."""
        # Build filter conditions
        conditions = []
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                conditions.append(getattr(self.model, key) == value)
        
        if conditions:
            result = await db.execute(select(self.model).where(*conditions))
            obj = result.scalar_one_or_none()
            
            if obj:
                return obj, False
        
        # Create new object
        create_data = kwargs.copy()
        if defaults:
            create_data.update(defaults)
        
        db_obj = self.model(**create_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        
        return db_obj, True

    async def bulk_create(
        self,
        db: AsyncSession,
        *,
        objs_in: List[CreateSchemaType]
    ) -> List[ModelType]:
        """Create multiple records in bulk."""
        db_objs = []
        for obj_in in objs_in:
            obj_in_data = jsonable_encoder(obj_in)
            db_obj = self.model(**obj_in_data)
            db_objs.append(db_obj)
        
        db.add_all(db_objs)
        await db.commit()
        
        for db_obj in db_objs:
            await db.refresh(db_obj)
        
        return db_objs

    async def bulk_update(
        self,
        db: AsyncSession,
        *,
        updates: List[Dict[str, Any]]
    ) -> int:
        """Update multiple records in bulk."""
        if not updates:
            return 0
        
        # Add updated_at timestamp if model supports it
        if hasattr(self.model, 'updated_at'):
            for update_data in updates:
                update_data['updated_at'] = datetime.utcnow()
        
        result = await db.execute(
            update(self.model),
            updates
        )
        await db.commit()
        return result.rowcount

    async def bulk_delete(
        self,
        db: AsyncSession,
        *,
        ids: List[Union[UUID, str, int]]
    ) -> int:
        """Delete multiple records in bulk."""
        if not ids:
            return 0
        
        result = await db.execute(
            delete(self.model).where(self.model.id.in_(ids))
        )
        await db.commit()
        return result.rowcount 