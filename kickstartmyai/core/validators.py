"""
Validation functions for project generation.
"""

import re
from typing import Optional


class ProjectValidationError(Exception):
    """Custom exception for project validation errors."""
    
    def __init__(self, field: str, message: str, value: Optional[str] = None):
        """
        Initialize validation error.
        
        Args:
            field: The field that failed validation
            message: Error message
            value: The invalid value (optional)
        """
        self.field = field
        self.message = message
        self.value = value
        
        error_msg = f"Validation error for '{field}': {message}"
        if value is not None:
            error_msg += f" (value: '{value}')"
        
        super().__init__(error_msg)


def validate_project_name(project_name: str) -> None:
    """
    Validate project name format.
    
    Rules:
    - Not empty and not just whitespace
    - Length between 1 and 100 characters
    - No newlines or tabs
    
    Args:
        project_name: The project name to validate
        
    Raises:
        ProjectValidationError: If validation fails
    """
    if not project_name or not project_name.strip():
        raise ProjectValidationError("project_name", "Project name cannot be empty", project_name)
    
    # Check length
    if len(project_name) > 100:
        raise ProjectValidationError("project_name", "Project name cannot be longer than 100 characters", project_name)
    
    # Check for invalid characters
    if '\n' in project_name or '\t' in project_name:
        raise ProjectValidationError("project_name", "Project name cannot contain newlines or tabs", project_name)


def validate_project_slug(project_slug: str) -> None:
    """
    Validate project slug format.
    
    Rules:
    - Only lowercase letters, numbers, hyphens, and underscores
    - Must start with a letter
    - Cannot start or end with hyphen/underscore
    - No consecutive special characters
    - Length between 2 and 50 characters
    
    Args:
        project_slug: The project slug to validate
        
    Raises:
        ProjectValidationError: If validation fails
    """
    if not project_slug:
        raise ProjectValidationError("project_slug", "Project slug cannot be empty", project_slug)
    
    # Check length
    if len(project_slug) < 2 or len(project_slug) > 50:
        raise ProjectValidationError("project_slug", "Project slug must be between 2 and 50 characters", project_slug)
    
    # Must start with a letter
    if not project_slug[0].isalpha():
        raise ProjectValidationError("project_slug", "Project slug must start with a letter", project_slug)
    
    # Only allowed characters: lowercase letters, numbers, hyphens, underscores
    if not re.match(r'^[a-z][a-z0-9_-]*$', project_slug):
        raise ProjectValidationError("project_slug", "Project slug can only contain lowercase letters, numbers, hyphens, and underscores", project_slug)
    
    # No consecutive special characters
    if re.search(r'[-_]{2,}', project_slug):
        raise ProjectValidationError("project_slug", "Project slug cannot have consecutive hyphens or underscores", project_slug)
    
    # Cannot end with special character
    if project_slug.endswith(('-', '_')):
        raise ProjectValidationError("project_slug", "Project slug cannot end with hyphen or underscore", project_slug)


def validate_email(email: str) -> None:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
        
    Raises:
        ProjectValidationError: If validation fails
    """
    if not email:
        raise ProjectValidationError("email", "Email cannot be empty", email)
    
    # Basic email regex pattern (more strict)
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9._%+-]*[a-zA-Z0-9]@[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]\.[a-zA-Z]{2,}$'
    
    # Check for consecutive dots
    if '..' in email:
        raise ProjectValidationError("email", "Email cannot contain consecutive dots", email)
    
    # Check for spaces
    if ' ' in email:
        raise ProjectValidationError("email", "Email cannot contain spaces", email)
    
    # Check general pattern
    if not re.match(pattern, email):
        raise ProjectValidationError("email", "Invalid email format", email)


def validate_python_package_name(name: str) -> bool:
    """
    Validate Python package name format.
    
    Args:
        name: Package name to validate
        
    Returns:
        True if valid Python package name, False otherwise
    """
    if not name:
        return False
    
    # Python package naming rules
    # - Must start with letter or underscore
    # - Can contain letters, numbers, underscores
    # - Cannot start with number
    # - Should be lowercase
    pattern = r'^[a-z_][a-z0-9_]*$'
    return bool(re.match(pattern, name))


def validate_aws_region(region: str) -> None:
    """
    Validate AWS region format.
    
    Args:
        region: AWS region to validate
        
    Raises:
        ProjectValidationError: If validation fails
    """
    if not region:
        raise ProjectValidationError("aws_region", "AWS region cannot be empty", region)
    
    # Common AWS regions pattern
    aws_regions = {
        'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
        'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-central-1',
        'eu-north-1', 'eu-south-1',
        'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1',
        'ap-northeast-2', 'ap-northeast-3', 'ap-south-1',
        'ap-east-1', 'ca-central-1', 'sa-east-1',
        'af-south-1', 'me-south-1'
    }
    
    if region not in aws_regions:
        raise ProjectValidationError("aws_region", f"Invalid AWS region. Must be one of: {', '.join(sorted(aws_regions))}", region)


def validate_database_name(name: str) -> bool:
    """
    Validate database name format.
    
    Args:
        name: Database name to validate
        
    Returns:
        True if valid database name, False otherwise
    """
    if not name:
        return False
    
    # Database naming rules (PostgreSQL compatible)
    # - Must start with letter or underscore
    # - Can contain letters, numbers, underscores
    # - Length between 1 and 63 characters
    if len(name) < 1 or len(name) > 63:
        return False
    
    pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
    return bool(re.match(pattern, name))


def sanitize_project_slug(project_name: str) -> str:
    """
    Convert project name to a valid slug format.
    
    Args:
        project_name: Original project name
        
    Returns:
        Sanitized project slug
    """
    # Convert to lowercase
    slug = project_name.lower()
    
    # Replace spaces and special characters with underscores
    slug = re.sub(r'[^a-z0-9_-]', '_', slug)
    
    # Remove consecutive underscores/hyphens
    slug = re.sub(r'[-_]+', '_', slug)
    
    # Remove leading/trailing underscores
    slug = slug.strip('_-')
    
    # Ensure it starts with a letter
    if slug and not slug[0].isalpha():
        slug = 'project_' + slug
    
    return slug or 'my_project'


def validate_version(version: str) -> bool:
    """
    Validate semantic version format.
    
    Args:
        version: Version string to validate
        
    Returns:
        True if valid semantic version, False otherwise
    """
    if not version:
        return False
    
    # Semantic versioning pattern (major.minor.patch)
    pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9-]+))?(?:\+([a-zA-Z0-9-]+))?$'
    return bool(re.match(pattern, version))
