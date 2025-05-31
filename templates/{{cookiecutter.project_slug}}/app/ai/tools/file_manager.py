"""File management tool for AI agents."""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import mimetypes
import hashlib
import logging
from pydantic import BaseModel, Field
import aiofiles
import aiofiles.os

from .base import BaseTool, ToolInput, ToolOutput

logger = logging.getLogger(__name__)


class FileReadInput(ToolInput):
    """Input schema for reading files."""
    
    file_path: str = Field(..., description="Path to the file to read")
    encoding: str = Field(default="utf-8", description="File encoding")
    max_size: int = Field(default=10*1024*1024, description="Maximum file size in bytes")


class FileWriteInput(ToolInput):
    """Input schema for writing files."""
    
    file_path: str = Field(..., description="Path to the file to write")
    content: str = Field(..., description="Content to write to the file")
    encoding: str = Field(default="utf-8", description="File encoding")
    create_directories: bool = Field(default=True, description="Create parent directories if they don't exist")
    backup: bool = Field(default=False, description="Create backup of existing file")


class FileListInput(ToolInput):
    """Input schema for listing directory contents."""
    
    directory_path: str = Field(..., description="Path to the directory to list")
    recursive: bool = Field(default=False, description="List files recursively")
    pattern: Optional[str] = Field(default=None, description="File pattern to match (glob style)")
    include_hidden: bool = Field(default=False, description="Include hidden files")
    max_depth: int = Field(default=10, description="Maximum recursion depth")


class FileDeleteInput(ToolInput):
    """Input schema for deleting files/directories."""
    
    path: str = Field(..., description="Path to delete")
    recursive: bool = Field(default=False, description="Delete directories recursively")
    backup: bool = Field(default=False, description="Create backup before deletion")


class FileCopyInput(ToolInput):
    """Input schema for copying files."""
    
    source_path: str = Field(..., description="Source file/directory path")
    destination_path: str = Field(..., description="Destination file/directory path")
    overwrite: bool = Field(default=False, description="Overwrite destination if it exists")
    preserve_metadata: bool = Field(default=True, description="Preserve file metadata")


class FileSearchInput(ToolInput):
    """Input schema for searching files."""
    
    directory_path: str = Field(..., description="Directory to search in")
    query: str = Field(..., description="Search query (text to find)")
    file_pattern: Optional[str] = Field(default=None, description="File pattern to search in")
    case_sensitive: bool = Field(default=False, description="Case-sensitive search")
    max_results: int = Field(default=100, description="Maximum number of results")
    include_line_numbers: bool = Field(default=True, description="Include line numbers in results")


class FileInfo(BaseModel):
    """File information model."""
    
    name: str = Field(..., description="File name")
    path: str = Field(..., description="Full file path")
    size: int = Field(..., description="File size in bytes")
    is_directory: bool = Field(..., description="Whether the path is a directory")
    is_file: bool = Field(..., description="Whether the path is a file")
    created_time: float = Field(..., description="Creation time (timestamp)")
    modified_time: float = Field(..., description="Last modification time (timestamp)")
    permissions: str = Field(..., description="File permissions")
    mime_type: Optional[str] = Field(default=None, description="MIME type")
    checksum: Optional[str] = Field(default=None, description="MD5 checksum for files")


class SearchResult(BaseModel):
    """File search result model."""
    
    file_path: str = Field(..., description="File path where match was found")
    line_number: int = Field(..., description="Line number of the match")
    line_content: str = Field(..., description="Content of the matching line")
    match_start: int = Field(..., description="Start position of match in line")
    match_end: int = Field(..., description="End position of match in line")


class FileReadOutput(ToolOutput):
    """Output schema for file reading."""
    
    content: str = Field(..., description="File content")
    file_info: FileInfo = Field(..., description="File information")
    encoding: str = Field(..., description="File encoding used")


class FileWriteOutput(ToolOutput):
    """Output schema for file writing."""
    
    success: bool = Field(..., description="Whether the write operation succeeded")
    file_info: FileInfo = Field(..., description="File information after writing")
    backup_path: Optional[str] = Field(default=None, description="Path to backup file if created")
    bytes_written: int = Field(..., description="Number of bytes written")


class FileListOutput(ToolOutput):
    """Output schema for directory listing."""
    
    files: List[FileInfo] = Field(..., description="List of files and directories")
    total_count: int = Field(..., description="Total number of items")
    directory_path: str = Field(..., description="Directory that was listed")


class FileDeleteOutput(ToolOutput):
    """Output schema for file deletion."""
    
    success: bool = Field(..., description="Whether the deletion succeeded")
    deleted_path: str = Field(..., description="Path that was deleted")
    backup_path: Optional[str] = Field(default=None, description="Path to backup if created")
    items_deleted: int = Field(default=1, description="Number of items deleted")


class FileCopyOutput(ToolOutput):
    """Output schema for file copying."""
    
    success: bool = Field(..., description="Whether the copy operation succeeded")
    source_info: FileInfo = Field(..., description="Source file information")
    destination_info: FileInfo = Field(..., description="Destination file information")
    bytes_copied: int = Field(..., description="Number of bytes copied")


class FileSearchOutput(ToolOutput):
    """Output schema for file searching."""
    
    results: List[SearchResult] = Field(..., description="Search results")
    total_matches: int = Field(..., description="Total number of matches found")
    files_searched: int = Field(..., description="Number of files searched")
    search_query: str = Field(..., description="Original search query")


class FileManagerTool(BaseTool):
    """Tool for managing files and directories."""
    
    name: str = "file_manager"
    description: str = "Read, write, copy, delete, and search files and directories"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize file manager tool."""
        super().__init__(config)
        self.allowed_paths = self.config.get("allowed_paths", [])
        self.blocked_paths = self.config.get("blocked_paths", ["/etc", "/bin", "/sbin", "/usr/bin"])
        self.max_file_size = self.config.get("max_file_size", 100 * 1024 * 1024)  # 100MB
        self.backup_directory = self.config.get("backup_directory", tempfile.gettempdir())
    
    def _validate_path(self, path: str) -> str:
        """Validate and normalize file path."""
        # Convert to absolute path
        abs_path = os.path.abspath(path)
        
        # Check blocked paths
        for blocked in self.blocked_paths:
            if abs_path.startswith(blocked):
                raise PermissionError(f"Access to path '{abs_path}' is blocked")
        
        # Check allowed paths (if specified)
        if self.allowed_paths:
            allowed = any(abs_path.startswith(allowed_path) for allowed_path in self.allowed_paths)
            if not allowed:
                raise PermissionError(f"Access to path '{abs_path}' is not allowed")
        
        return abs_path
    
    async def _get_file_info(self, path: str) -> FileInfo:
        """Get detailed file information."""
        abs_path = self._validate_path(path)
        
        try:
            stat_result = await aiofiles.os.stat(abs_path)
            
            # Get MIME type
            mime_type = None
            if os.path.isfile(abs_path):
                mime_type, _ = mimetypes.guess_type(abs_path)
            
            # Calculate checksum for files
            checksum = None
            if os.path.isfile(abs_path) and stat_result.st_size <= 50 * 1024 * 1024:  # 50MB limit
                checksum = await self._calculate_checksum(abs_path)
            
            # Get permissions
            permissions = oct(stat_result.st_mode)[-3:]
            
            return FileInfo(
                name=os.path.basename(abs_path),
                path=abs_path,
                size=stat_result.st_size,
                is_directory=os.path.isdir(abs_path),
                is_file=os.path.isfile(abs_path),
                created_time=stat_result.st_ctime,
                modified_time=stat_result.st_mtime,
                permissions=permissions,
                mime_type=mime_type,
                checksum=checksum
            )
        
        except Exception as e:
            logger.error(f"Error getting file info for {abs_path}: {e}")
            raise
    
    async def _calculate_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum of a file."""
        hash_md5 = hashlib.md5()
        
        async with aiofiles.open(file_path, "rb") as f:
            async for chunk in self._read_chunks(f):
                hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
    
    async def _read_chunks(self, file_obj, chunk_size: int = 8192):
        """Read file in chunks asynchronously."""
        while True:
            chunk = await file_obj.read(chunk_size)
            if not chunk:
                break
            yield chunk
    
    async def _create_backup(self, file_path: str) -> str:
        """Create a backup of a file."""
        if not os.path.exists(file_path):
            return None
        
        backup_name = f"{os.path.basename(file_path)}.backup.{int(asyncio.get_event_loop().time())}"
        backup_path = os.path.join(self.backup_directory, backup_name)
        
        await aiofiles.os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(file_path, backup_path)
        
        return backup_path
    
    async def read_file(self, tool_input: FileReadInput) -> FileReadOutput:
        """Read content from a file."""
        abs_path = self._validate_path(tool_input.file_path)
        
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"File not found: {abs_path}")
        
        if not os.path.isfile(abs_path):
            raise ValueError(f"Path is not a file: {abs_path}")
        
        # Check file size
        file_size = os.path.getsize(abs_path)
        if file_size > tool_input.max_size:
            raise ValueError(f"File too large: {file_size} bytes (max: {tool_input.max_size})")
        
        try:
            async with aiofiles.open(abs_path, "r", encoding=tool_input.encoding) as f:
                content = await f.read()
            
            file_info = await self._get_file_info(abs_path)
            
            return FileReadOutput(
                content=content,
                file_info=file_info,
                encoding=tool_input.encoding
            )
        
        except Exception as e:
            logger.error(f"Error reading file {abs_path}: {e}")
            raise
    
    async def write_file(self, tool_input: FileWriteInput) -> FileWriteOutput:
        """Write content to a file."""
        abs_path = self._validate_path(tool_input.file_path)
        
        # Create backup if requested and file exists
        backup_path = None
        if tool_input.backup and os.path.exists(abs_path):
            backup_path = await self._create_backup(abs_path)
        
        # Create parent directories if needed
        if tool_input.create_directories:
            parent_dir = os.path.dirname(abs_path)
            await aiofiles.os.makedirs(parent_dir, exist_ok=True)
        
        try:
            # Write content
            content_bytes = tool_input.content.encode(tool_input.encoding)
            
            async with aiofiles.open(abs_path, "w", encoding=tool_input.encoding) as f:
                await f.write(tool_input.content)
            
            file_info = await self._get_file_info(abs_path)
            
            return FileWriteOutput(
                success=True,
                file_info=file_info,
                backup_path=backup_path,
                bytes_written=len(content_bytes)
            )
        
        except Exception as e:
            logger.error(f"Error writing file {abs_path}: {e}")
            raise
    
    async def list_directory(self, tool_input: FileListInput) -> FileListOutput:
        """List directory contents."""
        abs_path = self._validate_path(tool_input.directory_path)
        
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Directory not found: {abs_path}")
        
        if not os.path.isdir(abs_path):
            raise ValueError(f"Path is not a directory: {abs_path}")
        
        files = []
        
        try:
            if tool_input.recursive:
                # Recursive listing
                for root, dirs, filenames in os.walk(abs_path):
                    # Check depth
                    depth = root[len(abs_path):].count(os.sep)
                    if depth >= tool_input.max_depth:
                        dirs.clear()  # Don't descend further
                        continue
                    
                    # Process directories
                    for dirname in dirs:
                        dir_path = os.path.join(root, dirname)
                        if tool_input.include_hidden or not dirname.startswith('.'):
                            file_info = await self._get_file_info(dir_path)
                            files.append(file_info)
                    
                    # Process files
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        if tool_input.include_hidden or not filename.startswith('.'):
                            # Apply pattern filter
                            if tool_input.pattern:
                                import fnmatch
                                if not fnmatch.fnmatch(filename, tool_input.pattern):
                                    continue
                            
                            file_info = await self._get_file_info(file_path)
                            files.append(file_info)
            else:
                # Non-recursive listing
                for item in os.listdir(abs_path):
                    if not tool_input.include_hidden and item.startswith('.'):
                        continue
                    
                    item_path = os.path.join(abs_path, item)
                    
                    # Apply pattern filter
                    if tool_input.pattern:
                        import fnmatch
                        if not fnmatch.fnmatch(item, tool_input.pattern):
                            continue
                    
                    file_info = await self._get_file_info(item_path)
                    files.append(file_info)
            
            return FileListOutput(
                files=files,
                total_count=len(files),
                directory_path=abs_path
            )
        
        except Exception as e:
            logger.error(f"Error listing directory {abs_path}: {e}")
            raise
    
    async def delete_path(self, tool_input: FileDeleteInput) -> FileDeleteOutput:
        """Delete a file or directory."""
        abs_path = self._validate_path(tool_input.path)
        
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Path not found: {abs_path}")
        
        # Create backup if requested
        backup_path = None
        if tool_input.backup:
            backup_path = await self._create_backup(abs_path)
        
        try:
            items_deleted = 1
            
            if os.path.isfile(abs_path):
                await aiofiles.os.remove(abs_path)
            elif os.path.isdir(abs_path):
                if tool_input.recursive:
                    # Count items before deletion
                    items_deleted = sum(len(files) + len(dirs) for _, dirs, files in os.walk(abs_path))
                    shutil.rmtree(abs_path)
                else:
                    await aiofiles.os.rmdir(abs_path)
            
            return FileDeleteOutput(
                success=True,
                deleted_path=abs_path,
                backup_path=backup_path,
                items_deleted=items_deleted
            )
        
        except Exception as e:
            logger.error(f"Error deleting {abs_path}: {e}")
            raise
    
    async def copy_path(self, tool_input: FileCopyInput) -> FileCopyOutput:
        """Copy a file or directory."""
        source_abs = self._validate_path(tool_input.source_path)
        dest_abs = self._validate_path(tool_input.destination_path)
        
        if not os.path.exists(source_abs):
            raise FileNotFoundError(f"Source not found: {source_abs}")
        
        if os.path.exists(dest_abs) and not tool_input.overwrite:
            raise FileExistsError(f"Destination already exists: {dest_abs}")
        
        try:
            # Get source info before copying
            source_info = await self._get_file_info(source_abs)
            
            bytes_copied = 0
            
            if os.path.isfile(source_abs):
                # Copy file
                if tool_input.preserve_metadata:
                    shutil.copy2(source_abs, dest_abs)
                else:
                    shutil.copy(source_abs, dest_abs)
                bytes_copied = source_info.size
            elif os.path.isdir(source_abs):
                # Copy directory
                if tool_input.preserve_metadata:
                    shutil.copytree(source_abs, dest_abs, dirs_exist_ok=tool_input.overwrite)
                else:
                    shutil.copytree(source_abs, dest_abs, dirs_exist_ok=tool_input.overwrite, copy_function=shutil.copy)
                
                # Calculate total bytes copied
                for root, dirs, files in os.walk(dest_abs):
                    for file in files:
                        file_path = os.path.join(root, file)
                        bytes_copied += os.path.getsize(file_path)
            
            dest_info = await self._get_file_info(dest_abs)
            
            return FileCopyOutput(
                success=True,
                source_info=source_info,
                destination_info=dest_info,
                bytes_copied=bytes_copied
            )
        
        except Exception as e:
            logger.error(f"Error copying {source_abs} to {dest_abs}: {e}")
            raise
    
    async def search_files(self, tool_input: FileSearchInput) -> FileSearchOutput:
        """Search for text within files."""
        abs_path = self._validate_path(tool_input.directory_path)
        
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Directory not found: {abs_path}")
        
        if not os.path.isdir(abs_path):
            raise ValueError(f"Path is not a directory: {abs_path}")
        
        results = []
        files_searched = 0
        
        try:
            for root, dirs, files in os.walk(abs_path):
                for filename in files:
                    # Apply file pattern filter
                    if tool_input.file_pattern:
                        import fnmatch
                        if not fnmatch.fnmatch(filename, tool_input.file_pattern):
                            continue
                    
                    file_path = os.path.join(root, filename)
                    
                    # Skip binary files
                    try:
                        mime_type, _ = mimetypes.guess_type(file_path)
                        if mime_type and not mime_type.startswith('text'):
                            continue
                    except:
                        continue
                    
                    # Search within file
                    try:
                        async with aiofiles.open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            files_searched += 1
                            line_number = 0
                            
                            async for line in f:
                                line_number += 1
                                line_content = line.rstrip('\n\r')
                                
                                # Perform search
                                search_text = tool_input.query if tool_input.case_sensitive else tool_input.query.lower()
                                search_line = line_content if tool_input.case_sensitive else line_content.lower()
                                
                                match_start = search_line.find(search_text)
                                if match_start != -1:
                                    match_end = match_start + len(search_text)
                                    
                                    result = SearchResult(
                                        file_path=file_path,
                                        line_number=line_number if tool_input.include_line_numbers else 0,
                                        line_content=line_content,
                                        match_start=match_start,
                                        match_end=match_end
                                    )
                                    results.append(result)
                                    
                                    # Check max results
                                    if len(results) >= tool_input.max_results:
                                        break
                            
                            if len(results) >= tool_input.max_results:
                                break
                    
                    except Exception as e:
                        logger.warning(f"Error searching file {file_path}: {e}")
                        continue
                
                if len(results) >= tool_input.max_results:
                    break
            
            return FileSearchOutput(
                results=results,
                total_matches=len(results),
                files_searched=files_searched,
                search_query=tool_input.query
            )
        
        except Exception as e:
            logger.error(f"Error searching files in {abs_path}: {e}")
            raise
    
    async def execute(self, tool_input: Union[FileReadInput, FileWriteInput, FileListInput, FileDeleteInput, FileCopyInput, FileSearchInput]) -> Union[FileReadOutput, FileWriteOutput, FileListOutput, FileDeleteOutput, FileCopyOutput, FileSearchOutput]:
        """Execute the file manager tool."""
        try:
            if isinstance(tool_input, FileReadInput):
                return await self.read_file(tool_input)
            elif isinstance(tool_input, FileWriteInput):
                return await self.write_file(tool_input)
            elif isinstance(tool_input, FileListInput):
                return await self.list_directory(tool_input)
            elif isinstance(tool_input, FileDeleteInput):
                return await self.delete_path(tool_input)
            elif isinstance(tool_input, FileCopyInput):
                return await self.copy_path(tool_input)
            elif isinstance(tool_input, FileSearchInput):
                return await self.search_files(tool_input)
            else:
                raise ValueError(f"Unsupported input type: {type(tool_input)}")
        
        except Exception as e:
            logger.error(f"File manager tool execution failed: {e}")
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
                        "enum": ["read", "write", "list", "delete", "copy", "search"],
                        "description": "Action to perform"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "File path (for read/write actions)"
                    },
                    "directory_path": {
                        "type": "string",
                        "description": "Directory path (for list/search actions)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write (for write action)"
                    },
                    "source_path": {
                        "type": "string",
                        "description": "Source path (for copy action)"
                    },
                    "destination_path": {
                        "type": "string",
                        "description": "Destination path (for copy action)"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (for search action)"
                    },
                    "recursive": {
                        "type": "boolean",
                        "default": False,
                        "description": "Recursive operation"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "File pattern to match"
                    }
                },
                "required": ["action"]
            }
        }
