"""Setup command - Configure platform authentication and create projects."""
import os
import re
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


def _extract_repo_info(repo_url: str):
    """Extract owner, repo name, and normalize URL from GitHub URL."""
    url = repo_url.strip()
    if url.endswith('.git'):
        url = url[:-4]

    if url.startswith("git@github.com:"):
        parts = url.replace("git@github.com:", "").split("/")
        if len(parts) == 2:
            owner, repo = parts[0], parts[1]
            return owner, repo, f"https://github.com/{owner}/{repo}.git"
    elif url.startswith("https://github.com/"):
        path = url[len("https://github.com/"):]
        # Handle possible trailing spaces in user input
        path = path.strip().rstrip('/')
        parts = path.split("/")
        if len(parts) == 2:
            owner, repo = parts[0], parts[1]
            return owner, repo, f"https://github.com/{owner}/{repo}.git"

    raise ValueError("Invalid GitHub URL. Use format: https://github.com/user/repo")


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
    
    # Initialize base handler config
    handler_config = {'token': token}

    # === RENDER-SPECIFIC FLOW: Full field collection ===
    if platform == "render":
        console.print("[bold cyan]🔗 Render deployment configuration[/bold cyan]")
        
        # 1. GitHub URL
        repo_url = Prompt.ask("GitHub repository URL (public)")
        try:
            owner, repo_name, normalized_url = _extract_repo_info(repo_url)
        except ValueError as e:
            console.print(f"\n[bold red]❌ {e}[/bold red]\n")
            raise typer.Exit(1)

        # 2. Project name
        safe_name = re.sub(r"[^a-z0-9\-]", "-", repo_name.lower())[:50]
        if not safe_name or not safe_name[0].isalpha():
            safe_name = "app-" + safe_name[-46:]
        project_name = Prompt.ask("Project name", default=safe_name)

        # 3. Language/Runtime
        language = Prompt.ask(
            "Language/Runtime",
            choices=["static", "node", "python", "go", "ruby", "docker"],
            default="static"
        )

        # 4. Branch
        branch = Prompt.ask("Branch", default="main")

        # 5. Root directory
        root_dir = Prompt.ask("Root directory (relative to repo root)", default="")

        # 6. Build command
        build_cmd = Prompt.ask("Build command (leave empty if none)", default="")

        # 7. Start command (for web services)
        start_cmd = ""
        if language != "static":
            start_cmd = Prompt.ask("Start command (e.g., 'npm start', 'gunicorn app:app')", default="")

        # 8. Instance type
        instance_type = "free"  # Render free tier
        if language != "static":
            instance_type = Prompt.ask(
                "Instance type",
                choices=["free", "starter", "standard", "pro"],
                default="free"
            )

        # 9. Environment variables
        env_vars = {}
        if Confirm.ask("Add environment variables?", default=False):
            while True:
                key = Prompt.ask("Env var name (or press Enter to finish)", default="")
                if not key:
                    break
                value = Prompt.ask(f"Value for {key}", password=True)
                env_vars[key] = value

        # Build config
        handler_config.update({
            'name': project_name,
            'repo': normalized_url,
            'branch': branch,
            'language': language,
            'root_directory': root_dir,
            'build_command': build_cmd,
            'start_command': start_cmd,
            'instance_type': instance_type,
            'env_vars': env_vars
        })

    else:
        # Other platforms: simplified flow
        default_name = config.get('name') or os.path.basename(os.getcwd())
        project_name = Prompt.ask("Project name", default=default_name)
        handler_config['name'] = project_name

    # Initialize platform handler
    handler_class = get_platform_handler(platform)
    if not handler_class:
        console.print(f"\n[bold red]❌ Platform handler not implemented:[/bold red] {platform}\n")
        raise typer.Exit(1)

    handler = handler_class(handler_config)
    
    # Authenticate
    console.print("[bold cyan]🔐 Authenticating...[/bold cyan]")
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("[cyan]Verifying credentials...", total=None)
        if not handler.authenticate():
            console.print("\n[bold red]❌ Authentication failed[/bold red]")
            console.print("[yellow]Please check your API token and try again[/yellow]\n")
            raise typer.Exit(1)
        progress.update(task, completed=True)
    
    console.print("[bold green]✅ Authentication successful![/bold green]\n")
    
    # Create project
    create_project = True if platform == "render" else Confirm.ask(
        f"Create a new project on {platform.capitalize()}?",
        default=True
    )

    if create_project:
        project_name = handler_config['name']
        console.print(f"\n[bold cyan]📦 Creating project '{project_name}'...[/bold cyan]")
        
        try:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
                task = progress.add_task("[cyan]Creating project...", total=None)
                project_id = handler.create_project()
                progress.update(task, completed=True)
            
            console.print(f"[bold green]✅ Project created:[/bold green] {project_id}\n")
            
            # Save config
            config.update({
                'platform': platform,
                'project_id': project_id,
                'project_name': project_name,
                **{k: v for k, v in handler_config.items() if k not in ['token']}
            })
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
