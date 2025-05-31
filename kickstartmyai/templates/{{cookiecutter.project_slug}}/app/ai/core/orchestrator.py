"""
Workflow Orchestrator - Manages complex AI workflows and task coordination.
"""

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field


class WorkflowStepType(str, Enum):
    """Types of workflow steps."""
    AI_TASK = "ai_task"
    TOOL_CALL = "tool_call"
    DECISION = "decision"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    CONDITION = "condition"
    LOOP = "loop"


class WorkflowStepStatus(str, Enum):
    """Status of workflow steps."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStep(BaseModel):
    """Individual step in a workflow."""
    
    id: str = Field(..., description="Unique identifier for the step")
    name: str = Field(..., description="Human-readable name for the step")
    type: WorkflowStepType = Field(..., description="Type of workflow step")
    description: Optional[str] = Field(None, description="Description of what this step does")
    
    # Step configuration
    config: Dict[str, Any] = Field(default_factory=dict, description="Step-specific configuration")
    dependencies: List[str] = Field(default_factory=list, description="IDs of steps this step depends on")
    timeout: Optional[int] = Field(None, description="Timeout in seconds")
    retry_count: int = Field(default=0, description="Number of retries on failure")
    
    # Execution state
    status: WorkflowStepStatus = Field(default=WorkflowStepStatus.PENDING)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    attempts: int = Field(default=0)


class Workflow(BaseModel):
    """Definition of a complete workflow."""
    
    id: str = Field(..., description="Unique identifier for the workflow")
    name: str = Field(..., description="Human-readable name for the workflow")
    description: Optional[str] = Field(None, description="Description of the workflow")
    version: str = Field(default="1.0", description="Version of the workflow")
    
    steps: List[WorkflowStep] = Field(..., description="List of workflow steps")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Expected input schema")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="Expected output schema")
    
    # Workflow configuration
    max_execution_time: int = Field(default=3600, description="Maximum execution time in seconds")
    parallel_limit: int = Field(default=5, description="Maximum parallel executions")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WorkflowExecution(BaseModel):
    """Runtime execution state of a workflow."""
    
    id: UUID = Field(default_factory=uuid4)
    workflow_id: str
    status: WorkflowStepStatus = Field(default=WorkflowStepStatus.PENDING)
    
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    
    step_results: Dict[str, Any] = Field(default_factory=dict)
    completed_steps: List[str] = Field(default_factory=list)
    failed_steps: List[str] = Field(default_factory=list)


class WorkflowOrchestrator:
    """
    Orchestrates complex AI workflows with multiple steps, dependencies, and parallel execution.
    """
    
    def __init__(self):
        """Initialize the workflow orchestrator."""
        self.workflows: Dict[str, Workflow] = {}
        self.executions: Dict[UUID, WorkflowExecution] = {}
        self.step_handlers: Dict[WorkflowStepType, Callable] = {
            WorkflowStepType.AI_TASK: self._handle_ai_task,
            WorkflowStepType.TOOL_CALL: self._handle_tool_call,
            WorkflowStepType.DECISION: self._handle_decision,
            WorkflowStepType.PARALLEL: self._handle_parallel,
            WorkflowStepType.SEQUENTIAL: self._handle_sequential,
            WorkflowStepType.CONDITION: self._handle_condition,
            WorkflowStepType.LOOP: self._handle_loop,
        }
    
    def register_workflow(self, workflow: Workflow) -> None:
        """Register a workflow definition."""
        self.workflows[workflow.id] = workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow definition by ID."""
        return self.workflows.get(workflow_id)
    
    def list_workflows(self) -> List[Workflow]:
        """List all registered workflows."""
        return list(self.workflows.values())
    
    async def execute_workflow(
        self,
        workflow_name: str,
        inputs: Dict[str, Any],
        agent: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow with the given inputs.
        
        Args:
            workflow_name: Name or ID of the workflow to execute
            inputs: Input parameters for the workflow
            agent: AI agent instance for AI tasks
            context: Additional context for execution
            
        Returns:
            Workflow execution results
        """
        # Find workflow
        workflow = self.workflows.get(workflow_name)
        if not workflow:
            # Try to find by name
            for wf in self.workflows.values():
                if wf.name == workflow_name:
                    workflow = wf
                    break
        
        if not workflow:
            raise ValueError(f"Workflow '{workflow_name}' not found")
        
        # Create execution
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            inputs=inputs,
            context=context or {},
            start_time=datetime.utcnow()
        )
        
        self.executions[execution.id] = execution
        
        try:
            # Execute workflow
            execution.status = WorkflowStepStatus.RUNNING
            await self._execute_workflow_steps(workflow, execution, agent)
            
            execution.status = WorkflowStepStatus.COMPLETED
            execution.end_time = datetime.utcnow()
            
            return {
                "execution_id": str(execution.id),
                "status": execution.status,
                "output": execution.outputs,
                "execution_time": (execution.end_time - execution.start_time).total_seconds(),
                "steps_executed": len(execution.completed_steps),
                "steps_failed": len(execution.failed_steps)
            }
            
        except Exception as e:
            execution.status = WorkflowStepStatus.FAILED
            execution.error = str(e)
            execution.end_time = datetime.utcnow()
            
            return {
                "execution_id": str(execution.id),
                "status": execution.status,
                "error": execution.error,
                "execution_time": (execution.end_time - execution.start_time).total_seconds(),
                "steps_executed": len(execution.completed_steps),
                "steps_failed": len(execution.failed_steps)
            }
    
    async def _execute_workflow_steps(
        self,
        workflow: Workflow,
        execution: WorkflowExecution,
        agent: Optional[Any] = None
    ) -> None:
        """Execute all steps in a workflow."""
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(workflow.steps)
        
        # Execute steps in dependency order
        executed_steps = set()
        
        while len(executed_steps) < len(workflow.steps):
            # Find steps ready to execute
            ready_steps = []
            for step in workflow.steps:
                if (step.id not in executed_steps and 
                    all(dep in executed_steps for dep in step.dependencies)):
                    ready_steps.append(step)
            
            if not ready_steps:
                break  # No more steps can be executed
            
            # Execute ready steps (potentially in parallel)
            parallel_tasks = []
            for step in ready_steps:
                if step.type == WorkflowStepType.PARALLEL:
                    # Handle parallel steps specially
                    parallel_tasks.append(self._execute_step(step, execution, agent))
                else:
                    # Execute step
                    await self._execute_step(step, execution, agent)
                    executed_steps.add(step.id)
            
            # Wait for parallel tasks
            if parallel_tasks:
                await asyncio.gather(*parallel_tasks)
                for step in ready_steps:
                    if step.type == WorkflowStepType.PARALLEL:
                        executed_steps.add(step.id)
    
    async def _execute_step(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
        agent: Optional[Any] = None
    ) -> None:
        """Execute a single workflow step."""
        step.start_time = datetime.utcnow()
        step.status = WorkflowStepStatus.RUNNING
        step.attempts += 1
        
        try:
            # Check timeout
            if step.timeout:
                result = await asyncio.wait_for(
                    self._execute_step_handler(step, execution, agent),
                    timeout=step.timeout
                )
            else:
                result = await self._execute_step_handler(step, execution, agent)
            
            step.result = result
            step.status = WorkflowStepStatus.COMPLETED
            step.end_time = datetime.utcnow()
            
            execution.step_results[step.id] = result
            execution.completed_steps.append(step.id)
            
        except Exception as e:
            step.error = str(e)
            step.status = WorkflowStepStatus.FAILED
            step.end_time = datetime.utcnow()
            
            execution.failed_steps.append(step.id)
            
            # Retry logic
            if step.attempts < step.retry_count + 1:
                step.status = WorkflowStepStatus.PENDING
                await asyncio.sleep(1)  # Brief delay before retry
                await self._execute_step(step, execution, agent)
            else:
                raise e
    
    async def _execute_step_handler(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
        agent: Optional[Any] = None
    ) -> Any:
        """Execute the appropriate handler for a step type."""
        handler = self.step_handlers.get(step.type)
        if not handler:
            raise ValueError(f"Unknown step type: {step.type}")
        
        return await handler(step, execution, agent)
    
    async def _handle_ai_task(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
        agent: Optional[Any] = None
    ) -> Any:
        """Handle AI task step."""
        if not agent:
            raise ValueError("AI agent required for AI task steps")
        
        prompt = step.config.get("prompt", "")
        
        # Replace variables in prompt
        for key, value in execution.context.items():
            prompt = prompt.replace(f"{{{key}}}", str(value))
        
        for key, value in execution.step_results.items():
            prompt = prompt.replace(f"{{{key}}}", str(value))
        
        response = await agent.chat(
            message=prompt,
            conversation_id=execution.id
        )
        
        return response.content
    
    async def _handle_tool_call(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
        agent: Optional[Any] = None
    ) -> Any:
        """Handle tool call step."""
        if not agent or not agent.executor:
            raise ValueError("AI agent with executor required for tool call steps")
        
        tool_name = step.config.get("tool_name")
        arguments = step.config.get("arguments", {})
        
        # Replace variables in arguments
        processed_args = {}
        for key, value in arguments.items():
            if isinstance(value, str):
                for ctx_key, ctx_value in execution.context.items():
                    value = value.replace(f"{{{ctx_key}}}", str(ctx_value))
                for step_key, step_value in execution.step_results.items():
                    value = value.replace(f"{{{step_key}}}", str(step_value))
            processed_args[key] = value
        
        result = await agent.executor.execute_tool(
            tool_name=tool_name,
            arguments=processed_args,
            context=execution.context
        )
        
        return result.result
    
    async def _handle_decision(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
        agent: Optional[Any] = None
    ) -> Any:
        """Handle decision step."""
        condition = step.config.get("condition")
        
        # Evaluate condition
        # This is a simple implementation - in practice, you might want
        # a more sophisticated expression evaluator
        context = {
            **execution.context,
            **execution.step_results
        }
        
        result = eval(condition, {"__builtins__": {}}, context)
        return result
    
    async def _handle_parallel(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
        agent: Optional[Any] = None
    ) -> Any:
        """Handle parallel execution step."""
        sub_steps = step.config.get("steps", [])
        
        tasks = []
        for sub_step_config in sub_steps:
            sub_step = WorkflowStep(**sub_step_config)
            tasks.append(self._execute_step(sub_step, execution, agent))
        
        results = await asyncio.gather(*tasks)
        return results
    
    async def _handle_sequential(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
        agent: Optional[Any] = None
    ) -> Any:
        """Handle sequential execution step."""
        sub_steps = step.config.get("steps", [])
        results = []
        
        for sub_step_config in sub_steps:
            sub_step = WorkflowStep(**sub_step_config)
            result = await self._execute_step(sub_step, execution, agent)
            results.append(result)
        
        return results
    
    async def _handle_condition(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
        agent: Optional[Any] = None
    ) -> Any:
        """Handle conditional execution step."""
        condition = step.config.get("condition")
        if_step = step.config.get("if_step")
        else_step = step.config.get("else_step")
        
        # Evaluate condition
        context = {
            **execution.context,
            **execution.step_results
        }
        
        condition_result = eval(condition, {"__builtins__": {}}, context)
        
        if condition_result and if_step:
            sub_step = WorkflowStep(**if_step)
            return await self._execute_step(sub_step, execution, agent)
        elif not condition_result and else_step:
            sub_step = WorkflowStep(**else_step)
            return await self._execute_step(sub_step, execution, agent)
        
        return None
    
    async def _handle_loop(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
        agent: Optional[Any] = None
    ) -> Any:
        """Handle loop execution step."""
        loop_step = step.config.get("loop_step")
        condition = step.config.get("condition")
        max_iterations = step.config.get("max_iterations", 10)
        
        results = []
        iteration = 0
        
        while iteration < max_iterations:
            # Evaluate condition
            context = {
                **execution.context,
                **execution.step_results,
                "iteration": iteration
            }
            
            if condition:
                condition_result = eval(condition, {"__builtins__": {}}, context)
                if not condition_result:
                    break
            
            # Execute loop step
            sub_step = WorkflowStep(**loop_step)
            result = await self._execute_step(sub_step, execution, agent)
            results.append(result)
            iteration += 1
        
        return results
    
    def _build_dependency_graph(self, steps: List[WorkflowStep]) -> Dict[str, List[str]]:
        """Build a dependency graph for workflow steps."""
        graph = {}
        for step in steps:
            graph[step.id] = step.dependencies
        return graph
    
    def get_execution_status(self, execution_id: UUID) -> Optional[Dict[str, Any]]:
        """Get the status of a workflow execution."""
        execution = self.executions.get(execution_id)
        if not execution:
            return None
        
        return {
            "execution_id": str(execution.id),
            "workflow_id": execution.workflow_id,
            "status": execution.status,
            "start_time": execution.start_time.isoformat() if execution.start_time else None,
            "end_time": execution.end_time.isoformat() if execution.end_time else None,
            "completed_steps": len(execution.completed_steps),
            "failed_steps": len(execution.failed_steps),
            "error": execution.error
        }
