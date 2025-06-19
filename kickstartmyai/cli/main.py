"""
KickStartMyAI CLI - Command Line Interface for generating FastAPI projects.
"""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ..core.generator import ProjectGenerator
from ..core.validators import validate_project_name, validate_email

app = typer.Typer(
    name="kickstartmyai",
    help="🚀 Generate production-ready FastAPI projects with AI capabilities",
    add_completion=False,
)

console = Console()


# Utility functions for CLI messages
def success_message(message: str):
    """Display a success message."""
    console.print(f"[green]✅ {message}[/green]")


def error_message(message: str):
    """Display an error message."""
    console.print(f"[red]❌ {message}[/red]")


def info_message(message: str):
    """Display an info message."""
    console.print(f"[blue]ℹ️ {message}[/blue]")


@app.command("create")
def create_project(
    project_name: Optional[str] = typer.Option(None, "--project-name", help="Name of the project to create"),
    project_slug: Optional[str] = typer.Option(None, "--project-slug", help="Project slug (URL-friendly name)"),
    output_dir: Optional[Path] = typer.Option(
        None, 
        "--output-dir", 
        "-o", 
        help="Output directory (default: current directory)"
    ),
    author_name: Optional[str] = typer.Option(
        None,
        "--author-name",
        "-a", 
        help="Author name"
    ),
    author_email: Optional[str] = typer.Option(
        None,
        "--author-email",
        "-e",
        help="Author email"
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Project description"
    ),
    database_type: Optional[str] = typer.Option(
        "postgresql",
        "--database-type",
        help="Database type (postgresql, mysql, sqlite)"
    ),
    aws_region: Optional[str] = typer.Option(
        "us-east-1",
        "--aws-region",
        help="AWS region for deployment"
    ),
    include_redis: bool = typer.Option(
        True,
        "--redis/--no-redis",
        help="Include Redis support"
    ),
    include_monitoring: bool = typer.Option(
        True,
        "--monitoring/--no-monitoring", 
        help="Include monitoring and observability"
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive/--no-interactive",
        "-i",
        help="Interactive mode with prompts"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing directory"
    ),
):
    """
    Create a new FastAPI project with AI capabilities.
    
    Example:
        kickstartmyai create --project-name "my-awesome-project" --author-name "John Doe" --author-email "john@example.com"
    """
    
    # Handle missing project name (only for non-interactive mode)
    if not project_name and not interactive:
        error_message("Project name is required. Use --project-name or --interactive mode.")
        raise typer.Exit(1)
    
    # Interactive mode (only prompt for fields not already provided)
    if interactive:
        if not project_name:
            project_name = typer.prompt("Project name")
        if not author_name:
            author_name = typer.prompt("Author name", default="Your Name")
        if not author_email:
            author_email = typer.prompt("Author email", default="your.email@example.com")
        if not description:
            description = typer.prompt(
                "Project description", 
                default="A FastAPI project with AI capabilities"
            )
        aws_region = typer.prompt("AWS region", default=aws_region)
        include_redis = typer.confirm("Include Redis support?", default=include_redis)
        include_monitoring = typer.confirm("Include monitoring?", default=include_monitoring)

    # Generate project slug if not provided
    if not project_slug and project_name:
        import re
        project_slug = re.sub(r'[^a-zA-Z0-9-_]', '-', project_name.lower())
        project_slug = re.sub(r'-+', '-', project_slug).strip('-')
    
    return _create_project_common(
        project_name=project_name,
        project_slug=project_slug,
        output_dir=output_dir,
        author_name=author_name,
        author_email=author_email,
        description=description,
        database_type=database_type,
        aws_region=aws_region,
        include_redis=include_redis,
        include_monitoring=include_monitoring,
        interactive=interactive,
        force=force
    )


@app.command("new")
def create_new_project(
    project_name: str = typer.Argument(..., help="Name of the project to create"),
    output_dir: Optional[Path] = typer.Option(
        None, 
        "--output-dir", 
        "-o", 
        help="Output directory (default: current directory)"
    ),
    author_name: Optional[str] = typer.Option(
        None,
        "--author",
        "-a", 
        help="Author name"
    ),
    author_email: Optional[str] = typer.Option(
        None,
        "--email",
        "-e",
        help="Author email"
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Project description"
    ),
    aws_region: Optional[str] = typer.Option(
        "us-east-1",
        "--aws-region",
        help="AWS region for deployment"
    ),
    include_redis: bool = typer.Option(
        True,
        "--redis/--no-redis",
        help="Include Redis support"
    ),
    include_monitoring: bool = typer.Option(
        True,
        "--monitoring/--no-monitoring", 
        help="Include monitoring and observability"
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Interactive mode with prompts"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing directory"
    ),
):
    """
    Create a new FastAPI project with AI capabilities.
    
    Example:
        kickstartmyai new my-awesome-project --author "John Doe" --email "john@example.com"
    """
    
    # Generate project slug
    import re
    project_slug = re.sub(r'[^a-zA-Z0-9-_]', '-', project_name.lower())
    project_slug = re.sub(r'-+', '-', project_slug).strip('-')
    
    return _create_project_common(
        project_name=project_name,
        project_slug=project_slug,
        output_dir=output_dir,
        author_name=author_name,
        author_email=author_email,
        description=description,
        database_type="postgresql",
        aws_region=aws_region,
        include_redis=include_redis,
        include_monitoring=include_monitoring,
        interactive=interactive,
        force=force
    )


def _create_project_common(
    project_name: str,
    project_slug: str,
    output_dir: Optional[Path],
    author_name: Optional[str],
    author_email: Optional[str],
    description: Optional[str],
    database_type: str,
    aws_region: str,
    include_redis: bool,
    include_monitoring: bool,
    interactive: bool,
    force: bool
):
    """Common implementation for project creation."""
    
    # Validate project name
    try:
        validate_project_name(project_name)
    except Exception as e:
        error_message(f"Invalid project name: {e}")
        raise typer.Exit(1)
    
    # Validate email if provided
    if author_email:
        try:
            validate_email(author_email)
        except Exception as e:
            error_message(f"Invalid email: {e}")
            raise typer.Exit(1)
    
    # Set defaults
    if not author_name:
        author_name = "Your Name"
    if not author_email:
        author_email = "your.email@example.com"
    if not description:
        description = "A FastAPI project with AI capabilities"
    
    # Set output directory
    if output_dir is None:
        output_dir = Path.cwd()
    
    target_path = output_dir / project_name
    
    # Check if directory exists
    if target_path.exists() and not force:
        error_message(f"Directory '{target_path}' already exists. Use --force to overwrite.")
        raise typer.Exit(1)
    
    # Show project info
    console.print()
    console.print(Panel.fit(
        Text.from_markup(f"""
[bold blue]🚀 Creating FastAPI Project[/bold blue]

[cyan]Project:[/cyan] {project_name}
[cyan]Author:[/cyan] {author_name} ({author_email})
[cyan]Description:[/cyan] {description}
[cyan]Output:[/cyan] {target_path}
[cyan]AWS Region:[/cyan] {aws_region}
[cyan]Redis:[/cyan] {"✅ Yes" if include_redis else "❌ No"}
[cyan]Monitoring:[/cyan] {"✅ Yes" if include_monitoring else "❌ No"}
        """.strip()),
        title="Project Configuration",
        border_style="blue"
    ))
    
    try:
        # Create the project
        generator = ProjectGenerator()
        
        with console.status("[bold blue]Generating project...", spinner="dots"):
            generator.generate_project(project_name)
        
        console.print()
        console.print(Panel.fit(
            Text.from_markup(f"""
[bold green]✅ Project created successfully![/bold green]

[cyan]Next steps:[/cyan]
1. cd {project_name}
2. python -m venv venv && source venv/bin/activate
3. pip install -r requirements.txt
4. cp .env.example .env
5. make dev-setup
6. make run

[yellow]📖 Check the README.md for detailed setup instructions.[/yellow]
            """.strip()),
            title="Success!",
            border_style="green"
        ))
        
        success_message("Project created successfully!")
        
    except Exception as e:
        error_message(f"Error creating project: {e}")
        raise typer.Exit(1)


@app.command("version")
def show_version():
    """Show the version of KickStartMyAI."""
    from .. import __version__
    console.print(f"KickStartMyAI version: [bold blue]{__version__}[/bold blue]")


@app.command("list-templates")
def list_templates():
    """List available project templates."""
    console.print(Panel.fit(
        Text.from_markup("""
[bold blue]📄 Available Templates[/bold blue]

[cyan]✅ FastAPI AI Template[/cyan] - Complete AI-powered FastAPI project
  • PostgreSQL database with async SQLAlchemy
  • AI provider integrations (OpenAI, Anthropic, Gemini)
  • Docker containerization
  • Authentication and authorization
  • Testing framework
  • CI/CD pipelines
        """.strip()),
        title="Project Templates",
        border_style="blue"
    ))


@app.command("validate")
def validate_template():
    """Validate the project template."""
    try:
        generator = ProjectGenerator()
        generator.validate_template()
        success_message("Template validation passed successfully!")
    except Exception as e:
        error_message(f"Template validation failed: {e}")
        raise typer.Exit(1)


@app.command("info")
def show_info():
    """Show information about KickStartMyAI."""
    console.print(Panel.fit(
        Text.from_markup("""
[bold blue]🚀 KickStartMyAI[/bold blue]

A production-ready FastAPI project generator that includes:

[cyan]✅ FastAPI[/cyan] - Modern, fast web framework
[cyan]✅ PostgreSQL[/cyan] - Robust database with migrations
[cyan]✅ Terraform[/cyan] - Infrastructure as Code (ECS deployment)
[cyan]✅ AI Providers[/cyan] - OpenAI, Anthropic, Gemini support
[cyan]✅ Security[/cyan] - JWT auth, encryption, validation
[cyan]✅ Testing[/cyan] - Unit, integration, e2e tests
[cyan]✅ Monitoring[/cyan] - Health checks, metrics, logging
[cyan]✅ CI/CD[/cyan] - GitHub Actions workflows
[cyan]✅ Docker[/cyan] - Development and production containers

[yellow]📖 Documentation: https://github.com/kickstartmyai/kickstartmyai[/yellow]
        """.strip()),
        title="About KickStartMyAI",
        border_style="blue"
    ))


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
