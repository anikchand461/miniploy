"""Run command - Trigger deployment and monitor status."""
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.live import Live
import time

from miniploy.config.manager import load_config, get_platform, get_project_id
from miniploy.platforms.factory import get_platform_handler

console = Console()


def run(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deployed without doing it"),
):
    """
    Trigger deployment to the configured platform.
    
    This command will:
    1. Load configuration from miniploy.yaml
    2. Trigger deployment on the platform
    3. Monitor deployment status
    4. Display logs and final URL
    """
    # Load config
    try:
        config = load_config()
    except Exception as e:
        console.print(f"\n[bold red]❌ Error loading configuration:[/bold red] {e}")
        console.print("\n[yellow]Run 'miniploy deploy' first to create a configuration[/yellow]\n")
        raise typer.Exit(1)
    
    # Validate config
    platform = get_platform(config)
    project_id = get_project_id(config)
    
    if not platform:
        console.print("\n[bold red]❌ No platform configured[/bold red]")
        console.print("\n[yellow]Run 'miniploy setup <platform>' first[/yellow]\n")
        raise typer.Exit(1)
    
    if not project_id:
        console.print("\n[bold red]❌ No project ID found[/bold red]")
        console.print("\n[yellow]Run 'miniploy setup <platform>' to create a project[/yellow]\n")
        raise typer.Exit(1)
    
    # Display what will be deployed
    console.print(f"\n[bold cyan]🚀 Deploying to {platform.capitalize()}...[/bold cyan]\n")
    
    deploy_info = Table(show_header=False, box=None)
    deploy_info.add_column("Key", style="cyan")
    deploy_info.add_column("Value", style="white")
    
    deploy_info.add_row("Platform", platform.capitalize())
    deploy_info.add_row("Project ID", project_id)
    deploy_info.add_row("Framework", config.get('framework', 'unknown'))
    deploy_info.add_row("Build Command", config.get('build_command', '(auto)'))
    deploy_info.add_row("Start Command", config.get('start_command', '(auto)'))
    
    console.print(Panel(
        deploy_info,
        title="[bold]📦 Deployment Info[/bold]",
        border_style="blue"
    ))
    
    if dry_run:
        console.print("\n[bold yellow]🔍 DRY RUN - No actual deployment triggered[/bold yellow]\n")
        return
    
    # Initialize platform handler
    handler_class = get_platform_handler(platform)
    if not handler_class:
        console.print(f"\n[bold red]❌ Platform handler not found:[/bold red] {platform}\n")
        raise typer.Exit(1)
    
    # Get token from config or environment
    import os
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
        console.print(f"\n[bold red]❌ API token not found in environment variable {env_var}[/bold red]\n")
        raise typer.Exit(1)
    
    handler_config = {
        'token': token,
        **config
    }
    
    handler = handler_class(handler_config)
    
    # Trigger deployment
    console.print("\n[bold cyan]🔨 Triggering deployment...[/bold cyan]\n")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Starting deployment...", total=None)
            deploy_id = handler.trigger_deploy(project_id)
            progress.update(task, completed=True)
        
        if deploy_id:
            console.print(f"[bold green]✅ Deployment started:[/bold green] {deploy_id}\n")
        else:
            console.print("[bold green]✅ Deployment triggered[/bold green]\n")
        
        # Monitor status
        console.print("[bold cyan]📊 Monitoring deployment status...[/bold cyan]\n")
        
        max_attempts = 30
        attempt = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Deploying...", total=max_attempts)
            
            while attempt < max_attempts:
                try:
                    status = handler.get_status(project_id)
                    state = status.get('state', 'UNKNOWN')
                    
                    progress.update(task, completed=attempt + 1)
                    
                    if state in ['READY', 'LIVE', 'ready', 'live', 'success']:
                        progress.update(task, description="[green]Deployment successful!")
                        break
                    elif state in ['ERROR', 'FAILED', 'error', 'failed']:
                        progress.update(task, description="[red]Deployment failed!")
                        break
                    else:
                        progress.update(task, description=f"[cyan]Deploying... ({state})")
                    
                    time.sleep(2)
                    attempt += 1
                    
                except Exception as e:
                    console.print(f"\n[yellow]⚠️  Status check failed: {e}[/yellow]")
                    break
        
        console.print()
        
        # Get final status and URL
        try:
            status = handler.get_status(project_id)
            state = status.get('state', 'UNKNOWN')
            url = handler.get_url(project_id)
            
            if state in ['READY', 'LIVE', 'ready', 'live', 'success']:
                result_panel = f"""[bold green]✅ Deployment Successful![/bold green]

[bold]Status:[/bold] {state}
[bold]URL:[/bold] {url or 'Check platform dashboard'}

[dim]View logs:[/dim] Check your {platform.capitalize()} dashboard"""
                
                console.print(Panel(
                    result_panel,
                    title="[bold green]🎉 Success[/bold green]",
                    border_style="green"
                ))
                
                if url:
                    console.print(f"\n[bold cyan]🌐 Visit your app:[/bold cyan] [link={url}]{url}[/link]\n")
            else:
                console.print(Panel(
                    f"[bold]Status:[/bold] {state}\n[bold]URL:[/bold] {url or 'Pending'}",
                    title="[bold yellow]⏳ Deployment In Progress[/bold yellow]",
                    border_style="yellow"
                ))
                console.print(f"\n[dim]Check platform dashboard for details[/dim]\n")
        
        except Exception as e:
            console.print(f"[yellow]⚠️  Could not retrieve final status: {e}[/yellow]\n")
    
    except Exception as e:
        console.print(f"\n[bold red]❌ Deployment failed:[/bold red] {e}\n")
        raise typer.Exit(1)
