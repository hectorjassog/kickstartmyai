"""
KickStartMyAI - FastAPI Project Generator with AI Capabilities

A production-ready FastAPI project generator that includes:
- PostgreSQL database setup
- Terraform infrastructure (ECS deployment)
- AI capabilities with multiple providers
- Best practices and security
"""

__version__ = "0.1.0"
__author__ = "KickStartMyAI Contributors"
__email__ = "contact@kickstartmyai.com"

from .core.generator import ProjectGenerator
from .core.validators import validate_project_name, validate_email

__all__ = [
    "ProjectGenerator",
    "validate_project_name", 
    "validate_email",
    "__version__",
]
