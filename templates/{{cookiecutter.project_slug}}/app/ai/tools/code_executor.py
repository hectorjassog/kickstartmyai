"""Code execution tool for AI agents."""

import asyncio
import tempfile
import subprocess
import os
import sys
import uuid
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import logging
from pydantic import BaseModel, Field
import docker
from docker.errors import DockerException

from .base import BaseTool, ToolInput, ToolOutput

logger = logging.getLogger(__name__)


class CodeExecutionInput(ToolInput):
    """Input schema for code execution tool."""
    
    code: str = Field(..., description="Code to execute")
    language: str = Field(..., description="Programming language (python, javascript, bash, etc.)")
    timeout: int = Field(default=30, ge=1, le=300, description="Execution timeout in seconds")
    working_directory: Optional[str] = Field(default=None, description="Working directory for execution")
    environment_variables: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    requirements: List[str] = Field(default_factory=list, description="Package requirements (for Python)")
    allow_network: bool = Field(default=False, description="Allow network access during execution")
    memory_limit: str = Field(default="512m", description="Memory limit for Docker container")


class CodeExecutionOutput(ToolOutput):
    """Output schema for code execution tool."""
    
    stdout: str = Field(..., description="Standard output")
    stderr: str = Field(..., description="Standard error")
    exit_code: int = Field(..., description="Exit code")
    execution_time: float = Field(..., description="Execution time in seconds")
    language: str = Field(..., description="Programming language used")
    files_created: List[str] = Field(default_factory=list, description="Files created during execution")
    error_message: Optional[str] = Field(default=None, description="Error message if execution failed")


class CodeSnippetInput(ToolInput):
    """Input schema for code snippet analysis."""
    
    code: str = Field(..., description="Code to analyze")
    language: str = Field(..., description="Programming language")
    analysis_type: str = Field(
        default="syntax", 
        description="Type of analysis (syntax, security, complexity, style)"
    )


class CodeSnippetOutput(ToolOutput):
    """Output schema for code snippet analysis."""
    
    is_valid: bool = Field(..., description="Whether code is syntactically valid")
    issues: List[str] = Field(default_factory=list, description="Issues found in the code")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    complexity_score: Optional[int] = Field(default=None, description="Complexity score (1-10)")
    security_warnings: List[str] = Field(default_factory=list, description="Security warnings")


class CodeExecutorTool(BaseTool):
    """Tool for executing code in various programming languages."""
    
    name: str = "code_executor"
    description: str = "Execute code safely in isolated environments and analyze code snippets"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize code executor tool."""
        super().__init__(config)
        self.use_docker = self.config.get("use_docker", True)
        self.docker_client = None
        self.temp_dir = tempfile.mkdtemp(prefix="code_executor_")
        
        # Supported languages and their configurations
        self.language_configs = {
            "python": {
                "extension": ".py",
                "docker_image": "python:3.11-slim",
                "command": ["python"],
                "setup_commands": []
            },
            "javascript": {
                "extension": ".js",
                "docker_image": "node:18-slim",
                "command": ["node"],
                "setup_commands": []
            },
            "typescript": {
                "extension": ".ts",
                "docker_image": "node:18-slim",
                "command": ["npx", "ts-node"],
                "setup_commands": ["npm install -g typescript ts-node"]
            },
            "bash": {
                "extension": ".sh",
                "docker_image": "ubuntu:22.04",
                "command": ["bash"],
                "setup_commands": []
            },
            "go": {
                "extension": ".go",
                "docker_image": "golang:1.21-slim",
                "command": ["go", "run"],
                "setup_commands": []
            },
            "rust": {
                "extension": ".rs",
                "docker_image": "rust:1.75-slim",
                "command": ["rustc", "--edition", "2021", "-o", "/tmp/program"],
                "setup_commands": []
            }
        }
        
        if self.use_docker:
            self._init_docker()
    
    def _init_docker(self):
        """Initialize Docker client."""
        try:
            self.docker_client = docker.from_env()
            # Test Docker connection
            self.docker_client.ping()
            logger.info("Docker client initialized successfully")
        except DockerException as e:
            logger.error(f"Failed to initialize Docker: {e}")
            self.use_docker = False
            logger.warning("Falling back to local execution (less secure)")
    
    async def _execute_in_docker(
        self,
        code: str,
        language: str,
        timeout: int,
        working_directory: Optional[str] = None,
        environment_variables: Optional[Dict[str, str]] = None,
        requirements: Optional[List[str]] = None,
        allow_network: bool = False,
        memory_limit: str = "512m"
    ) -> CodeExecutionOutput:
        """Execute code in a Docker container."""
        if not self.docker_client:
            raise Exception("Docker client not available")
        
        if language not in self.language_configs:
            raise ValueError(f"Unsupported language: {language}")
        
        config = self.language_configs[language]
        execution_id = str(uuid.uuid4())[:8]
        
        # Create temporary files
        temp_dir = Path(self.temp_dir) / execution_id
        temp_dir.mkdir(exist_ok=True)
        
        code_file = temp_dir / f"script{config['extension']}"
        code_file.write_text(code)
        
        import time
        start_time = time.time()
        
        try:
            # Prepare Docker run parameters
            volumes = {str(temp_dir): {"bind": "/workspace", "mode": "rw"}}
            working_dir = "/workspace"
            
            environment = environment_variables or {}
            
            # Network configuration
            network_mode = "bridge" if allow_network else "none"
            
            # Create and setup container
            container = self.docker_client.containers.run(
                config["docker_image"],
                command="sleep infinity",  # Keep container running
                volumes=volumes,
                working_dir=working_dir,
                environment=environment,
                network_mode=network_mode,
                mem_limit=memory_limit,
                detach=True,
                remove=True
            )
            
            try:
                # Install requirements if needed
                if requirements and language == "python":
                    for req in requirements:
                        exec_result = container.exec_run(
                            f"pip install {req}",
                            workdir=working_dir
                        )
                        if exec_result.exit_code != 0:
                            logger.warning(f"Failed to install {req}: {exec_result.output.decode()}")
                
                # Run setup commands
                for setup_cmd in config["setup_commands"]:
                    container.exec_run(setup_cmd, workdir=working_dir)
                
                # Execute the code
                command = config["command"] + [f"script{config['extension']}"]
                
                exec_result = container.exec_run(
                    command,
                    workdir=working_dir,
                    timeout=timeout
                )
                
                execution_time = time.time() - start_time
                
                # Get list of files created
                files_result = container.exec_run("find /workspace -type f -name '*' | grep -v script", workdir=working_dir)
                files_created = []
                if files_result.exit_code == 0:
                    files_output = files_result.output.decode().strip()
                    if files_output:
                        files_created = [f.replace("/workspace/", "") for f in files_output.split("\n")]
                
                return CodeExecutionOutput(
                    stdout=exec_result.output.decode() if exec_result.output else "",
                    stderr="",
                    exit_code=exec_result.exit_code,
                    execution_time=execution_time,
                    language=language,
                    files_created=files_created
                )
            
            finally:
                container.stop()
        
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Docker execution failed: {e}")
            return CodeExecutionOutput(
                stdout="",
                stderr=str(e),
                exit_code=1,
                execution_time=execution_time,
                language=language,
                error_message=str(e)
            )
        
        finally:
            # Clean up temporary files
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    async def _execute_locally(
        self,
        code: str,
        language: str,
        timeout: int,
        working_directory: Optional[str] = None,
        environment_variables: Optional[Dict[str, str]] = None
    ) -> CodeExecutionOutput:
        """Execute code locally (less secure)."""
        if language not in self.language_configs:
            raise ValueError(f"Unsupported language: {language}")
        
        config = self.language_configs[language]
        execution_id = str(uuid.uuid4())[:8]
        
        # Create temporary files
        temp_dir = Path(self.temp_dir) / execution_id
        temp_dir.mkdir(exist_ok=True)
        
        code_file = temp_dir / f"script{config['extension']}"
        code_file.write_text(code)
        
        import time
        start_time = time.time()
        
        try:
            # Prepare environment
            env = os.environ.copy()
            if environment_variables:
                env.update(environment_variables)
            
            # Prepare command
            command = config["command"] + [str(code_file)]
            
            # Execute
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_directory or temp_dir,
                env=env
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                execution_time = time.time() - start_time
                
                # Get list of files created
                files_created = []
                for file_path in temp_dir.iterdir():
                    if file_path.name != code_file.name:
                        files_created.append(file_path.name)
                
                return CodeExecutionOutput(
                    stdout=stdout.decode() if stdout else "",
                    stderr=stderr.decode() if stderr else "",
                    exit_code=process.returncode or 0,
                    execution_time=execution_time,
                    language=language,
                    files_created=files_created
                )
            
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                execution_time = time.time() - start_time
                
                return CodeExecutionOutput(
                    stdout="",
                    stderr="Execution timed out",
                    exit_code=124,  # Standard timeout exit code
                    execution_time=execution_time,
                    language=language,
                    error_message="Execution timed out"
                )
        
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Local execution failed: {e}")
            return CodeExecutionOutput(
                stdout="",
                stderr=str(e),
                exit_code=1,
                execution_time=execution_time,
                language=language,
                error_message=str(e)
            )
        
        finally:
            # Clean up temporary files
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    async def _analyze_code(self, code: str, language: str, analysis_type: str) -> CodeSnippetOutput:
        """Analyze code snippet for various issues."""
        issues = []
        suggestions = []
        security_warnings = []
        is_valid = True
        complexity_score = None
        
        try:
            if language == "python":
                # Basic syntax check
                try:
                    compile(code, "<string>", "exec")
                except SyntaxError as e:
                    is_valid = False
                    issues.append(f"Syntax error: {e}")
                
                # Security analysis
                dangerous_imports = ["os", "subprocess", "sys", "eval", "exec"]
                for imp in dangerous_imports:
                    if f"import {imp}" in code or f"from {imp}" in code:
                        security_warnings.append(f"Potentially dangerous import: {imp}")
                
                if "eval(" in code:
                    security_warnings.append("Use of eval() can be dangerous")
                if "exec(" in code:
                    security_warnings.append("Use of exec() can be dangerous")
                
                # Complexity analysis (basic)
                lines = code.split("\n")
                complexity_indicators = sum(1 for line in lines if any(keyword in line for keyword in ["if", "for", "while", "try", "except"]))
                complexity_score = min(10, max(1, complexity_indicators))
                
                # Style suggestions
                if not code.strip():
                    suggestions.append("Empty code block")
                elif not any(line.strip().startswith("#") for line in lines):
                    suggestions.append("Consider adding comments to explain the code")
            
            elif language == "javascript":
                # Basic checks for JavaScript
                if "eval(" in code:
                    security_warnings.append("Use of eval() can be dangerous")
                if "document.write(" in code:
                    security_warnings.append("document.write() can be vulnerable to XSS")
                
                # Count cyclomatic complexity indicators
                complexity_indicators = sum(1 for keyword in ["if", "for", "while", "switch", "catch"] if keyword in code)
                complexity_score = min(10, max(1, complexity_indicators))
            
            else:
                # Generic analysis for other languages
                if code.strip():
                    complexity_score = 5  # Default complexity
                else:
                    is_valid = False
                    issues.append("Empty code block")
        
        except Exception as e:
            logger.error(f"Code analysis failed: {e}")
            issues.append(f"Analysis error: {e}")
        
        return CodeSnippetOutput(
            is_valid=is_valid,
            issues=issues,
            suggestions=suggestions,
            complexity_score=complexity_score,
            security_warnings=security_warnings
        )
    
    async def execute_code(self, tool_input: CodeExecutionInput) -> CodeExecutionOutput:
        """Execute code in the specified language."""
        if self.use_docker and self.docker_client:
            return await self._execute_in_docker(
                tool_input.code,
                tool_input.language,
                tool_input.timeout,
                tool_input.working_directory,
                tool_input.environment_variables,
                tool_input.requirements,
                tool_input.allow_network,
                tool_input.memory_limit
            )
        else:
            return await self._execute_locally(
                tool_input.code,
                tool_input.language,
                tool_input.timeout,
                tool_input.working_directory,
                tool_input.environment_variables
            )
    
    async def analyze_code(self, tool_input: CodeSnippetInput) -> CodeSnippetOutput:
        """Analyze code snippet."""
        return await self._analyze_code(
            tool_input.code,
            tool_input.language,
            tool_input.analysis_type
        )
    
    async def execute(self, tool_input: Union[CodeExecutionInput, CodeSnippetInput]) -> Union[CodeExecutionOutput, CodeSnippetOutput]:
        """Execute the code executor tool."""
        try:
            if isinstance(tool_input, CodeExecutionInput):
                return await self.execute_code(tool_input)
            elif isinstance(tool_input, CodeSnippetInput):
                return await self.analyze_code(tool_input)
            else:
                raise ValueError(f"Unsupported input type: {type(tool_input)}")
        
        except Exception as e:
            logger.error(f"Code executor tool execution failed: {e}")
            raise
    
    async def cleanup(self):
        """Clean up resources."""
        # Clean up temporary directory
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
        # Close Docker client
        if self.docker_client:
            self.docker_client.close()
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported programming languages."""
        return list(self.language_configs.keys())
    
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
                        "enum": ["execute", "analyze"],
                        "description": "Action to perform"
                    },
                    "code": {
                        "type": "string",
                        "description": "Code to execute or analyze"
                    },
                    "language": {
                        "type": "string",
                        "enum": list(self.language_configs.keys()),
                        "description": "Programming language"
                    },
                    "timeout": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 300,
                        "default": 30,
                        "description": "Execution timeout in seconds"
                    },
                    "requirements": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Package requirements (Python only)"
                    },
                    "allow_network": {
                        "type": "boolean",
                        "default": False,
                        "description": "Allow network access during execution"
                    }
                },
                "required": ["action", "code", "language"]
            }
        }
