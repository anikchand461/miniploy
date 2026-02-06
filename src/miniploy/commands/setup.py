"""Setup command - Configure platform authentication and create projects."""
import os
import configparser
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

from miniploy.config.manager import load_config, save_config
from miniploy.platforms.factory import get_platform_handler

console = Console()

SUPPORTED_PLATFORMS = ["vercel", "netlify", "render", "railway", "flyio"]


def _get_git_remote(project_path: Path) -> str:
    git_config = project_path / ".git" / "config"
    if not git_config.exists():
        return ""
    config = configparser.ConfigParser()
    config.read(git_config)
    for section in config.sections():
        if section.lower().startswith("remote ") and config.has_option(section, "url"):
            return config.get(section, "url")
    return ""


def _get_git_branch(project_path: Path) -> str:
    head_file = project_path / ".git" / "HEAD"
    if not head_file.exists():
        return ""
    try:
        head = head_file.read_text(encoding="utf-8").strip()
        if head.startswith("ref:"):
            return head.split("/", 2)[-1]
    except Exception:
        return ""
    return ""


def setup(
    platform: str = typer.Argument(None, help="Target platform: vercel | netlify | render | railway | flyio"),
    project: str = typer.Option(".", "--project", "-p", help="Project path"),
):
    """
    Set up authentication and create a project on the chosen platform.
    
    This command will:
    1. Prompt for API token if not found in environment
    2. Verify authentication
    3. Create a new project/app/site on the platform
    4. Save configuration to miniploy.yaml
    """
    # List platforms if none specified
    if not platform:
        console.print("\n[bold cyan]📋 Available Platforms:[/bold cyan]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Platform", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Best For", style="green")
        
        table.add_row("vercel", "Vercel Platform", "Next.js, React, Static Sites")
        table.add_row("netlify", "Netlify", "JAMstack, Static Sites")
        table.add_row("render", "Render", "Full-stack, Docker, Web Services")
        table.add_row("railway", "Railway", "Databases, Backend Services")
        table.add_row("flyio", "Fly.io", "Containers, Global Apps")
        
        console.print(table)
        console.print("\n[dim]Usage: miniploy setup <platform>[/dim]\n")
        return
    
    # Validate platform
    platform = platform.lower()
    if platform not in SUPPORTED_PLATFORMS:
        console.print(f"\n[bold red]❌ Unknown platform:[/bold red] {platform}")
        console.print(f"[yellow]Supported platforms:[/yellow] {', '.join(SUPPORTED_PLATFORMS)}\n")
        raise typer.Exit(1)
    
    console.print(f"\n[bold cyan]🚀 Setting up {platform.capitalize()}...[/bold cyan]\n")
    
    # Load existing config
    try:
        config = load_config()
    except Exception:
        config = {}
    
    # Get token from environment or prompt
    token_env_vars = {
        'vercel': 'VERCEL_TOKEN',
        'netlify': 'NETLIFY_TOKEN',
        'render': 'RENDER_TOKEN',
        'railway': 'RAILWAY_TOKEN',
        'flyio': 'FLY_API_TOKEN'
    }
    
    env_var = token_env_vars.get(platform, f'{platform.upper()}_TOKEN')
    token = os.getenv(env_var)
    
    if not token:
        console.print(f"[yellow]ℹ️  API token not found in environment variable {env_var}[/yellow]")
        console.print(f"\n[bold cyan]📌 Get your token from:[/bold cyan]")
        
        token_urls = {
            'vercel': 'https://vercel.com/account/settings/tokens',
            'netlify': 'https://app.netlify.com/user/applications/personal',
            'render': 'https://dashboard.render.com/u/settings?add-api-key',
            'railway': 'https://railway.com/account/tokens',
            'flyio': 'https://fly.io/user/personal_access_tokens'
        }
        
        url = token_urls.get(platform, 'Platform dashboard')
        console.print(f"  🔗 {url}\n")
        
        token = Prompt.ask(f"Enter your {platform.capitalize()} API token", password=True)
        
        if not token:
            console.print("\n[bold red]❌ Token is required[/bold red]\n")
            raise typer.Exit(1)
    
    # Initialize platform handler
    handler_class = get_platform_handler(platform)
    if not handler_class:
        console.print(f"\n[bold red]❌ Platform handler not implemented:[/bold red] {platform}\n")
        raise typer.Exit(1)
    
    project_path = Path(project).resolve()

    handler_config = {
        'token': token,
        'name': config.get('name', os.path.basename(os.getcwd())),
        'framework': config.get('framework'),
        'build_command': config.get('build_command'),
        'start_command': config.get('start_command'),
        'runtime': config.get('runtime'),
        'dockerfile': config.get('dockerfile'),
        'project_path': str(project_path),
        'repo_url': config.get('repo_url'),
        'branch': config.get('branch')
    }

    # Infer docker runtime if Dockerfile exists
    if not handler_config.get('runtime'):
        dockerfile = project_path / (handler_config.get('dockerfile') or 'Dockerfile')
        if dockerfile.exists():
            handler_config['runtime'] = 'docker'
            config['runtime'] = 'docker'
            config['dockerfile'] = dockerfile.name

    # Docker-specific hints
    if handler_config.get('runtime') == 'docker':
        if platform in {'vercel', 'netlify'}:
            console.print("\n[bold yellow]⚠️  Docker deployments are not supported on Vercel/Netlify in miniploy[/bold yellow]\n")
        if platform == 'render':
            repo_url = handler_config.get('repo_url') or _get_git_remote(project_path)
            if not repo_url:
                repo_url = Prompt.ask("Git repository URL for Render (required for Docker deploy)")
            branch = handler_config.get('branch') or _get_git_branch(project_path) or "main"
            dockerfile_path = handler_config.get('dockerfile') or "Dockerfile"
            handler_config['repo_url'] = repo_url
            handler_config['branch'] = branch
            handler_config['dockerfile'] = dockerfile_path
            config['repo_url'] = repo_url
            config['branch'] = branch
            config['dockerfile'] = dockerfile_path
    elif platform == 'render':
        repo_url = handler_config.get('repo_url') or _get_git_remote(project_path)
        if not repo_url:
            repo_url = Prompt.ask("Git repository URL for Render (required for deploy)")
        handler_config['repo_url'] = repo_url
        handler_config['branch'] = handler_config.get('branch') or _get_git_branch(project_path) or "main"
        config['repo_url'] = handler_config['repo_url']
        config['branch'] = handler_config['branch']
    
    handler = handler_class(handler_config)
    
    # Authenticate
    console.print("[bold cyan]🔐 Authenticating...[/bold cyan]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Verifying credentials...", total=None)
        
        if not handler.authenticate():
            console.print("\n[bold red]❌ Authentication failed[/bold red]")
            console.print("[yellow]Please check your API token and try again[/yellow]\n")
            raise typer.Exit(1)
        
        progress.update(task, completed=True)
    
    console.print("[bold green]✅ Authentication successful![/bold green]\n")
    
    # Create project
    create_project = Confirm.ask(
        f"Create a new project on {platform.capitalize()}?",
        default=True
    )
    
    if create_project:
        project_name = Prompt.ask(
            "Project name",
            default=handler_config['name']
        )
        
        handler_config['name'] = project_name
        handler.config['name'] = project_name
        
        console.print(f"\n[bold cyan]📦 Creating project '{project_name}'...[/bold cyan]")
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("[cyan]Creating project...", total=None)
                project_id = handler.create_project()
                progress.update(task, completed=True)
            
            console.print(f"[bold green]✅ Project created:[/bold green] {project_id}\n")
            
            # Update config
            config['platform'] = platform
            config['project_id'] = project_id
            config['project_name'] = project_name
            config['project_path'] = handler_config.get('project_path')
            if handler_config.get('runtime'):
                config['runtime'] = handler_config.get('runtime')
            if handler_config.get('dockerfile'):
                config['dockerfile'] = handler_config.get('dockerfile')
            if handler_config.get('repo_url'):
                config['repo_url'] = handler_config.get('repo_url')
            if handler_config.get('branch'):
                config['branch'] = handler_config.get('branch')
            
            # Set environment variables if needed
            env_vars_needed = config.get('env_vars', {})
            if env_vars_needed and Confirm.ask("Set environment variables now?", default=False):
                console.print("\n[bold cyan]🔐 Setting environment variables...[/bold cyan]")
                
                env_vars = {}
                for var_name in env_vars_needed:
                    value = Prompt.ask(f"  {var_name}", password=True)
                    if value:
                        env_vars[var_name] = value
                
                if env_vars:
                    handler.set_env_vars(project_id, env_vars)
                    console.print("[bold green]✅ Environment variables set[/bold green]\n")
            
            # Save config
            config_path = save_config(config)
            console.print(f"[bold green]✅ Configuration saved to {config_path}[/bold green]\n")
            
            # Show next steps
            console.print(Panel(
                f"""[bold]Platform:[/bold] {platform}
[bold]Project ID:[/bold] {project_id}
[bold]Project Name:[/bold] {project_name}

[dim]Next step:[/dim]
  [cyan]miniploy run[/cyan] - Deploy your application""",
                title="[bold green]✅ Setup Complete[/bold green]",
                border_style="green"
            ))
            
        except Exception as e:
            console.print(f"\n[bold red]❌ Error creating project:[/bold red] {e}\n")
            raise typer.Exit(1)
    else:
        console.print("\n[yellow]Project creation skipped[/yellow]\n")
