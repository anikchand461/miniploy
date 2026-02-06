"""Manage command - View all your deployments across platforms."""
import os
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from miniploy.platforms.vercel import VercelHandler
from miniploy.platforms.netlify import NetlifyHandler
from miniploy.platforms.render import RenderHandler
from miniploy.platforms.railway import RailwayHandler
from miniploy.platforms.flyio import FlyioHandler

console = Console()


def manage(
    platform: str = typer.Option(None, "--platform", "-p", help="Filter by platform: vercel | netlify | render | railway | flyio"),
):
    """
    View all your deployments across platforms.
    
    Shows a list of all projects/sites you've deployed with their URLs.
    
    Example:
        miniploy manage                    # Show all deployments
        miniploy manage --platform vercel  # Show only Vercel deployments
    """
    
    console.print("\n[bold cyan]📦 Your Deployments[/bold cyan]\n")
    
    # Define platforms to check
    if platform:
        platforms_to_check = {platform.lower(): None}
    else:
        platforms_to_check = {
            'vercel': None,
            'netlify': None,
            'render': None,
            'railway': None,
            'flyio': None
        }
    
    # Token mapping
    token_env_vars = {
        'vercel': 'VERCEL_TOKEN',
        'netlify': 'NETLIFY_TOKEN',
        'render': 'RENDER_TOKEN',
        'railway': 'RAILWAY_TOKEN',
        'flyio': 'FLY_API_TOKEN'
    }
    
    # Handler mapping
    handler_classes = {
        'vercel': VercelHandler,
        'netlify': NetlifyHandler,
        'render': RenderHandler,
        'railway': RailwayHandler,
        'flyio': FlyioHandler
    }
    
    all_deployments = []
    
    # Check each platform
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        for platform_name in platforms_to_check.keys():
            task = progress.add_task(f"[cyan]Checking {platform_name.capitalize()}...", total=None)
            
            # Get token
            token = os.getenv(token_env_vars.get(platform_name))
            
            if not token:
                progress.update(task, description=f"[dim]{platform_name.capitalize()}: No token[/dim]")
                continue
            
            try:
                # Initialize handler
                handler = handler_classes[platform_name]({'token': token})
                
                # Authenticate
                if not handler.authenticate():
                    progress.update(task, description=f"[yellow]{platform_name.capitalize()}: Auth failed[/yellow]")
                    continue
                
                # Get deployments
                deployments = handler.list_deployments()
                
                for deployment in deployments:
                    all_deployments.append({
                        'platform': platform_name.capitalize(),
                        'name': deployment.get('name', 'N/A'),
                        'url': deployment.get('url', 'N/A'),
                        'status': deployment.get('status', 'Unknown'),
                        'created': deployment.get('created_at', 'N/A')
                    })
                
                progress.update(task, description=f"[green]{platform_name.capitalize()}: {len(deployments)} found[/green]")
                
            except Exception as e:
                progress.update(task, description=f"[red]{platform_name.capitalize()}: Error[/red]")
    
    console.print()
    
    # Display results
    if not all_deployments:
        console.print("[yellow]No deployments found.[/yellow]")
        console.print("\n[dim]Tip: Deploy something first with 'miniploy static' or 'miniploy run'[/dim]\n")
        return
    
    # Create table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Platform", style="cyan", width=12)
    table.add_column("Name", style="white", width=30)
    table.add_column("URL", style="green", width=50)
    table.add_column("Status", style="yellow", width=12)
    
    for deployment in all_deployments:
        url = deployment['url']
        if url and not url.startswith('http'):
            url = f"https://{url}"
        
        # Truncate long names/URLs for display
        name = deployment['name'][:28] + "..." if len(deployment['name']) > 30 else deployment['name']
        display_url = url[:48] + "..." if len(url) > 50 else url
        
        table.add_row(
            deployment['platform'],
            name,
            display_url,
            deployment['status']
        )
    
    console.print(Panel(
        table,
        title=f"[bold]📊 Total Deployments: {len(all_deployments)}[/bold]",
        border_style="blue"
    ))
    
    console.print()
