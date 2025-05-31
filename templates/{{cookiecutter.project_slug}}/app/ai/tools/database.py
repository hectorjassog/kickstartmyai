"""Database tool for AI agents."""

import asyncio
from typing import Any, Dict, List, Optional, Union
import logging
from pydantic import BaseModel, Field
from sqlalchemy import text, MetaData, Table, inspect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd

from .base import BaseTool, ToolInput, ToolOutput
from ...database import get_async_session

logger = logging.getLogger(__name__)


class DatabaseQueryInput(ToolInput):
    """Input schema for database queries."""
    
    query: str = Field(..., description="SQL query to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Query parameters")
    fetch_mode: str = Field(default="all", description="Fetch mode: 'all', 'one', 'many'")
    limit: Optional[int] = Field(default=None, ge=1, le=10000, description="Limit number of results")
    read_only: bool = Field(default=True, description="Whether query is read-only")


class DatabaseSchemaInput(ToolInput):
    """Input schema for database schema inspection."""
    
    table_name: Optional[str] = Field(default=None, description="Specific table to inspect")
    include_data_types: bool = Field(default=True, description="Include column data types")
    include_constraints: bool = Field(default=True, description="Include table constraints")
    include_indexes: bool = Field(default=False, description="Include index information")


class DatabaseExecuteInput(ToolInput):
    """Input schema for database operations."""
    
    operation: str = Field(..., description="Operation to perform: insert, update, delete, create_table")
    table_name: str = Field(..., description="Target table name")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Data for insert/update operations")
    where_clause: Optional[str] = Field(default=None, description="WHERE clause for update/delete")
    schema_definition: Optional[str] = Field(default=None, description="Table schema for create_table")


class DatabaseAnalysisInput(ToolInput):
    """Input schema for database analysis."""
    
    table_name: str = Field(..., description="Table to analyze")
    analysis_type: str = Field(default="summary", description="Type of analysis: summary, distribution, correlations")
    columns: Optional[List[str]] = Field(default=None, description="Specific columns to analyze")
    sample_size: int = Field(default=1000, ge=1, le=100000, description="Sample size for analysis")


class TableInfo(BaseModel):
    """Table information model."""
    
    name: str = Field(..., description="Table name")
    columns: List[Dict[str, Any]] = Field(..., description="Column information")
    row_count: Optional[int] = Field(default=None, description="Number of rows")
    constraints: List[Dict[str, Any]] = Field(default_factory=list, description="Table constraints")
    indexes: List[Dict[str, Any]] = Field(default_factory=list, description="Table indexes")


class QueryResult(BaseModel):
    """Query result model."""
    
    columns: List[str] = Field(..., description="Column names")
    rows: List[List[Any]] = Field(..., description="Result rows")
    row_count: int = Field(..., description="Number of rows returned")
    execution_time: float = Field(..., description="Query execution time in seconds")


class DatabaseQueryOutput(ToolOutput):
    """Output schema for database queries."""
    
    result: QueryResult = Field(..., description="Query result")
    query: str = Field(..., description="Executed query")
    success: bool = Field(..., description="Whether query succeeded")
    message: Optional[str] = Field(default=None, description="Success/error message")


class DatabaseSchemaOutput(ToolOutput):
    """Output schema for database schema inspection."""
    
    tables: List[TableInfo] = Field(..., description="Database tables information")
    total_tables: int = Field(..., description="Total number of tables")
    database_name: Optional[str] = Field(default=None, description="Database name")


class DatabaseExecuteOutput(ToolOutput):
    """Output schema for database operations."""
    
    success: bool = Field(..., description="Whether operation succeeded")
    affected_rows: int = Field(..., description="Number of affected rows")
    operation: str = Field(..., description="Operation performed")
    message: Optional[str] = Field(default=None, description="Success/error message")
    execution_time: float = Field(..., description="Operation execution time in seconds")


class DatabaseAnalysisOutput(ToolOutput):
    """Output schema for database analysis."""
    
    analysis_type: str = Field(..., description="Type of analysis performed")
    table_name: str = Field(..., description="Table analyzed")
    summary: Dict[str, Any] = Field(..., description="Analysis summary")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed analysis results")
    recommendations: List[str] = Field(default_factory=list, description="Analysis recommendations")


class DatabaseTool(BaseTool):
    """Tool for interacting with databases."""
    
    name: str = "database"
    description: str = "Execute database queries, inspect schema, and perform data analysis"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize database tool."""
        super().__init__(config)
        self.session_factory = None
        self.allowed_operations = self.config.get("allowed_operations", ["SELECT", "INSERT", "UPDATE", "DELETE"])
        self.max_results = self.config.get("max_results", 10000)
        self.query_timeout = self.config.get("query_timeout", 60)
        self.read_only_mode = self.config.get("read_only_mode", False)
    
    async def _get_session(self) -> AsyncSession:
        """Get database session."""
        if self.session_factory is None:
            # Use the application's database session
            async for session in get_async_session():
                return session
        return self.session_factory()
    
    def _validate_query(self, query: str, read_only: bool = True) -> str:
        """Validate and clean SQL query."""
        query = query.strip()
        
        # Remove comments and normalize
        lines = []
        for line in query.split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):
                lines.append(line)
        
        query = ' '.join(lines)
        
        # Extract operation type
        operation = query.split()[0].upper()
        
        # Check if operation is allowed
        if operation not in self.allowed_operations:
            raise ValueError(f"Operation '{operation}' is not allowed")
        
        # Enforce read-only mode
        if (read_only or self.read_only_mode) and operation not in ["SELECT", "SHOW", "DESCRIBE", "EXPLAIN"]:
            raise ValueError(f"Write operation '{operation}' not allowed in read-only mode")
        
        # Basic SQL injection prevention
        dangerous_keywords = ["DROP", "TRUNCATE", "ALTER", "GRANT", "REVOKE"]
        for keyword in dangerous_keywords:
            if keyword in query.upper():
                raise ValueError(f"Dangerous keyword '{keyword}' detected in query")
        
        return query
    
    async def _execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        fetch_mode: str = "all",
        limit: Optional[int] = None
    ) -> QueryResult:
        """Execute a database query."""
        import time
        start_time = time.time()
        
        # Apply limit if specified
        if limit and "LIMIT" not in query.upper():
            query = f"{query} LIMIT {limit}"
        elif limit is None and self.max_results:
            query = f"{query} LIMIT {self.max_results}"
        
        async with self._get_session() as session:
            try:
                # Execute query
                result = await session.execute(text(query), parameters or {})
                
                # Fetch results based on mode
                if fetch_mode == "one":
                    row = result.fetchone()
                    rows = [list(row)] if row else []
                elif fetch_mode == "many":
                    rows = [list(row) for row in result.fetchmany(size=limit or 100)]
                else:  # "all"
                    rows = [list(row) for row in result.fetchall()]
                
                # Get column names
                columns = list(result.keys()) if result.keys() else []
                
                execution_time = time.time() - start_time
                
                return QueryResult(
                    columns=columns,
                    rows=rows,
                    row_count=len(rows),
                    execution_time=execution_time
                )
            
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Query execution failed: {e}")
                raise Exception(f"Query execution failed: {str(e)}")
    
    async def _get_table_info(self, session: AsyncSession, table_name: str) -> TableInfo:
        """Get detailed information about a table."""
        inspector = inspect(session.bind)
        
        # Get columns
        columns = []
        try:
            for column in inspector.get_columns(table_name):
                columns.append({
                    "name": column["name"],
                    "type": str(column["type"]),
                    "nullable": column["nullable"],
                    "default": column.get("default"),
                    "primary_key": column.get("primary_key", False)
                })
        except Exception as e:
            logger.error(f"Error getting columns for table {table_name}: {e}")
        
        # Get constraints
        constraints = []
        try:
            # Primary key
            pk = inspector.get_pk_constraint(table_name)
            if pk and pk.get("constrained_columns"):
                constraints.append({
                    "type": "PRIMARY KEY",
                    "columns": pk["constrained_columns"],
                    "name": pk.get("name")
                })
            
            # Foreign keys
            for fk in inspector.get_foreign_keys(table_name):
                constraints.append({
                    "type": "FOREIGN KEY",
                    "columns": fk["constrained_columns"],
                    "referenced_table": fk["referred_table"],
                    "referenced_columns": fk["referred_columns"],
                    "name": fk.get("name")
                })
            
            # Unique constraints
            for uc in inspector.get_unique_constraints(table_name):
                constraints.append({
                    "type": "UNIQUE",
                    "columns": uc["column_names"],
                    "name": uc.get("name")
                })
        
        except Exception as e:
            logger.error(f"Error getting constraints for table {table_name}: {e}")
        
        # Get indexes
        indexes = []
        try:
            for index in inspector.get_indexes(table_name):
                indexes.append({
                    "name": index["name"],
                    "columns": index["column_names"],
                    "unique": index.get("unique", False)
                })
        except Exception as e:
            logger.error(f"Error getting indexes for table {table_name}: {e}")
        
        # Get row count
        row_count = None
        try:
            result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            row_count = result.scalar()
        except Exception as e:
            logger.error(f"Error getting row count for table {table_name}: {e}")
        
        return TableInfo(
            name=table_name,
            columns=columns,
            row_count=row_count,
            constraints=constraints,
            indexes=indexes
        )
    
    async def _analyze_table(
        self,
        table_name: str,
        analysis_type: str,
        columns: Optional[List[str]] = None,
        sample_size: int = 1000
    ) -> Dict[str, Any]:
        """Perform statistical analysis on a table."""
        async with self._get_session() as session:
            try:
                # Get table schema first
                table_info = await self._get_table_info(session, table_name)
                
                if not table_info.columns:
                    return {"error": "No columns found in table"}
                
                # Select columns to analyze
                if columns is None:
                    columns = [col["name"] for col in table_info.columns]
                
                # Build query
                column_list = ", ".join(columns)
                query = f"SELECT {column_list} FROM {table_name} LIMIT {sample_size}"
                
                result = await session.execute(text(query))
                rows = result.fetchall()
                
                if not rows:
                    return {"error": "No data found in table"}
                
                # Convert to DataFrame for analysis
                df = pd.DataFrame(rows, columns=columns)
                
                analysis_results = {}
                
                if analysis_type == "summary":
                    # Basic summary statistics
                    analysis_results = {
                        "total_rows": len(rows),
                        "total_columns": len(columns),
                        "numeric_summary": df.describe().to_dict() if not df.empty else {},
                        "null_counts": df.isnull().sum().to_dict(),
                        "data_types": df.dtypes.astype(str).to_dict()
                    }
                
                elif analysis_type == "distribution":
                    # Data distribution analysis
                    analysis_results = {}
                    for column in columns:
                        if column in df.columns:
                            if df[column].dtype in ['int64', 'float64']:
                                analysis_results[column] = {
                                    "type": "numeric",
                                    "min": float(df[column].min()) if not df[column].empty else None,
                                    "max": float(df[column].max()) if not df[column].empty else None,
                                    "mean": float(df[column].mean()) if not df[column].empty else None,
                                    "std": float(df[column].std()) if not df[column].empty else None,
                                    "quartiles": df[column].quantile([0.25, 0.5, 0.75]).to_dict()
                                }
                            else:
                                # Categorical distribution
                                value_counts = df[column].value_counts().head(10)
                                analysis_results[column] = {
                                    "type": "categorical",
                                    "unique_values": int(df[column].nunique()),
                                    "top_values": value_counts.to_dict()
                                }
                
                elif analysis_type == "correlations":
                    # Correlation analysis for numeric columns
                    numeric_columns = df.select_dtypes(include=['int64', 'float64']).columns
                    if len(numeric_columns) > 1:
                        correlations = df[numeric_columns].corr()
                        analysis_results = {
                            "correlations": correlations.to_dict(),
                            "strong_correlations": []
                        }
                        
                        # Find strong correlations (> 0.7 or < -0.7)
                        for i, col1 in enumerate(numeric_columns):
                            for j, col2 in enumerate(numeric_columns):
                                if i < j:  # Avoid duplicates
                                    corr_value = correlations.loc[col1, col2]
                                    if abs(corr_value) > 0.7:
                                        analysis_results["strong_correlations"].append({
                                            "column1": col1,
                                            "column2": col2,
                                            "correlation": float(corr_value)
                                        })
                    else:
                        analysis_results = {"error": "Need at least 2 numeric columns for correlation analysis"}
                
                return analysis_results
            
            except Exception as e:
                logger.error(f"Table analysis failed: {e}")
                return {"error": str(e)}
    
    async def execute_query(self, tool_input: DatabaseQueryInput) -> DatabaseQueryOutput:
        """Execute a database query."""
        try:
            # Validate query
            validated_query = self._validate_query(tool_input.query, tool_input.read_only)
            
            # Execute query
            result = await self._execute_query(
                validated_query,
                tool_input.parameters,
                tool_input.fetch_mode,
                tool_input.limit
            )
            
            return DatabaseQueryOutput(
                result=result,
                query=validated_query,
                success=True,
                message=f"Query executed successfully. Returned {result.row_count} rows."
            )
        
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return DatabaseQueryOutput(
                result=QueryResult(columns=[], rows=[], row_count=0, execution_time=0),
                query=tool_input.query,
                success=False,
                message=str(e)
            )
    
    async def inspect_schema(self, tool_input: DatabaseSchemaInput) -> DatabaseSchemaOutput:
        """Inspect database schema."""
        async with self._get_session() as session:
            try:
                inspector = inspect(session.bind)
                table_names = inspector.get_table_names()
                
                tables = []
                
                if tool_input.table_name:
                    # Inspect specific table
                    if tool_input.table_name in table_names:
                        table_info = await self._get_table_info(session, tool_input.table_name)
                        tables.append(table_info)
                    else:
                        raise ValueError(f"Table '{tool_input.table_name}' not found")
                else:
                    # Inspect all tables
                    for table_name in table_names:
                        table_info = await self._get_table_info(session, table_name)
                        tables.append(table_info)
                
                return DatabaseSchemaOutput(
                    tables=tables,
                    total_tables=len(tables),
                    database_name=session.bind.url.database
                )
            
            except Exception as e:
                logger.error(f"Schema inspection failed: {e}")
                raise
    
    async def execute_operation(self, tool_input: DatabaseExecuteInput) -> DatabaseExecuteOutput:
        """Execute database operations."""
        import time
        start_time = time.time()
        
        if self.read_only_mode:
            raise ValueError("Write operations not allowed in read-only mode")
        
        async with self._get_session() as session:
            try:
                affected_rows = 0
                
                if tool_input.operation == "insert" and tool_input.data:
                    # Insert operation
                    columns = ", ".join(tool_input.data.keys())
                    placeholders = ", ".join([f":{key}" for key in tool_input.data.keys()])
                    query = f"INSERT INTO {tool_input.table_name} ({columns}) VALUES ({placeholders})"
                    
                    result = await session.execute(text(query), tool_input.data)
                    affected_rows = result.rowcount
                    await session.commit()
                
                elif tool_input.operation == "update" and tool_input.data:
                    # Update operation
                    set_clause = ", ".join([f"{key} = :{key}" for key in tool_input.data.keys()])
                    query = f"UPDATE {tool_input.table_name} SET {set_clause}"
                    
                    if tool_input.where_clause:
                        query += f" WHERE {tool_input.where_clause}"
                    
                    result = await session.execute(text(query), tool_input.data)
                    affected_rows = result.rowcount
                    await session.commit()
                
                elif tool_input.operation == "delete":
                    # Delete operation
                    query = f"DELETE FROM {tool_input.table_name}"
                    
                    if tool_input.where_clause:
                        query += f" WHERE {tool_input.where_clause}"
                    else:
                        raise ValueError("DELETE operation requires WHERE clause for safety")
                    
                    result = await session.execute(text(query))
                    affected_rows = result.rowcount
                    await session.commit()
                
                elif tool_input.operation == "create_table" and tool_input.schema_definition:
                    # Create table operation
                    query = f"CREATE TABLE {tool_input.table_name} ({tool_input.schema_definition})"
                    await session.execute(text(query))
                    await session.commit()
                    affected_rows = 1
                
                else:
                    raise ValueError(f"Unsupported operation: {tool_input.operation}")
                
                execution_time = time.time() - start_time
                
                return DatabaseExecuteOutput(
                    success=True,
                    affected_rows=affected_rows,
                    operation=tool_input.operation,
                    message=f"Operation '{tool_input.operation}' completed successfully",
                    execution_time=execution_time
                )
            
            except Exception as e:
                await session.rollback()
                execution_time = time.time() - start_time
                logger.error(f"Database operation failed: {e}")
                
                return DatabaseExecuteOutput(
                    success=False,
                    affected_rows=0,
                    operation=tool_input.operation,
                    message=str(e),
                    execution_time=execution_time
                )
    
    async def analyze_data(self, tool_input: DatabaseAnalysisInput) -> DatabaseAnalysisOutput:
        """Perform data analysis on a table."""
        try:
            analysis_results = await self._analyze_table(
                tool_input.table_name,
                tool_input.analysis_type,
                tool_input.columns,
                tool_input.sample_size
            )
            
            # Generate recommendations based on analysis
            recommendations = []
            
            if tool_input.analysis_type == "summary":
                if "null_counts" in analysis_results:
                    for column, null_count in analysis_results["null_counts"].items():
                        if null_count > 0:
                            recommendations.append(f"Column '{column}' has {null_count} null values - consider data cleaning")
            
            elif tool_input.analysis_type == "correlations":
                if "strong_correlations" in analysis_results:
                    for corr in analysis_results["strong_correlations"]:
                        recommendations.append(f"Strong correlation ({corr['correlation']:.2f}) between {corr['column1']} and {corr['column2']}")
            
            return DatabaseAnalysisOutput(
                analysis_type=tool_input.analysis_type,
                table_name=tool_input.table_name,
                summary={"status": "Analysis completed successfully"},
                details=analysis_results,
                recommendations=recommendations
            )
        
        except Exception as e:
            logger.error(f"Data analysis failed: {e}")
            return DatabaseAnalysisOutput(
                analysis_type=tool_input.analysis_type,
                table_name=tool_input.table_name,
                summary={"status": "Analysis failed", "error": str(e)},
                details={"error": str(e)},
                recommendations=[]
            )
    
    async def execute(self, tool_input: Union[DatabaseQueryInput, DatabaseSchemaInput, DatabaseExecuteInput, DatabaseAnalysisInput]) -> Union[DatabaseQueryOutput, DatabaseSchemaOutput, DatabaseExecuteOutput, DatabaseAnalysisOutput]:
        """Execute the database tool."""
        try:
            if isinstance(tool_input, DatabaseQueryInput):
                return await self.execute_query(tool_input)
            elif isinstance(tool_input, DatabaseSchemaInput):
                return await self.inspect_schema(tool_input)
            elif isinstance(tool_input, DatabaseExecuteInput):
                return await self.execute_operation(tool_input)
            elif isinstance(tool_input, DatabaseAnalysisInput):
                return await self.analyze_data(tool_input)
            else:
                raise ValueError(f"Unsupported input type: {type(tool_input)}")
        
        except Exception as e:
            logger.error(f"Database tool execution failed: {e}")
            raise
    
    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema for function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["query", "schema", "execute", "analyze"],
                        "description": "Action to perform"
                    },
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute (for query action)"
                    },
                    "table_name": {
                        "type": "string",
                        "description": "Table name"
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["insert", "update", "delete", "create_table"],
                        "description": "Database operation (for execute action)"
                    },
                    "data": {
                        "type": "object",
                        "description": "Data for database operations"
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": ["summary", "distribution", "correlations"],
                        "description": "Type of analysis (for analyze action)"
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10000,
                        "description": "Limit number of results"
                    }
                },
                "required": ["action"]
            }
        }
