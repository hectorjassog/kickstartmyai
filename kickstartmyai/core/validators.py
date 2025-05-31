"""
Validation functions for project generation.
"""

import re
from typing import Optional


def validate_project_name(project_name: str) -> bool:
    """
    Validate project name format.
    
    Rules:
    - Only letters, numbers, hyphens, and underscores
    - Must start with a letter
    - Length between 2 and 50 characters
    - No consecutive special characters
    
    Args:
        project_name: The project name to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not project_name:
        return False
    
    # Check length
    if len(project_name) < 2 or len(project_name) > 50:
        return False
    
    # Must start with a letter
    if not project_name[0].isalpha():
        return False
    
    # Only allowed characters: letters, numbers, hyphens, underscores
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', project_name):
        return False
    
    # No consecutive special characters
    if re.search(r'[-_]{2,}', project_name):
        return False
    
    # Cannot end with special character
    if project_name.endswith(('-', '_')):
        return False
    
    return True


def validate_email(email: str) -> bool:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid email format, False otherwise
    """
    if not email:
        return False
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


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


def validate_aws_region(region: str) -> bool:
    """
    Validate AWS region format.
    
    Args:
        region: AWS region to validate
        
    Returns:
        True if valid AWS region format, False otherwise
    """
    if not region:
        return False
    
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
    
    return region in aws_regions


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
