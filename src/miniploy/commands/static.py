"""Static deployment command - Deploy static files to platforms."""
import os
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm

from miniploy.platforms.vercel import VercelHandler
from miniploy.platforms.netlify import NetlifyHandler

console = Console()


def static(
    path: str = typer.Argument(".", help="Directory containing static files"),
    platform: str = typer.Option("vercel", "--platform", "-p", help="Platform: vercel | netlify"),
    name: str = typer.Option(None, "--name", "-n", help="Deployment name"),
):
    """
    Deploy static files (HTML, CSS, JS) directly to a platform.
    
    Perfect for deploying simple websites without build steps.
    Supports: Vercel, Netlify
    
    Example:
        miniploy static .
        miniploy static ./my-site --platform netlify
        miniploy static ./my-site --name my-awesome-site --platform vercel
    """
    
    # Validate path
    files_path = Path(path).resolve()
    if not files_path.exists():
        console.print(f"\n[bold red]❌ Path not found:[/bold red] {path}\n")
        raise typer.Exit(1)
    
    if not files_path.is_dir():
        console.print(f"\n[bold red]❌ Path must be a directory:[/bold red] {path}\n")
        raise typer.Exit(1)
    
    # Check for index.html
    index_file = files_path / 'index.html'
    if not index_file.exists():
        console.print(f"\n[bold yellow]⚠️  No index.html found in {path}[/bold yellow]")
        if not Confirm.ask("Continue anyway?", default=False):
            raise typer.Exit(0)
    
    # Generate deployment name
    if not name:
        name = files_path.name
        console.print(f"\n[dim]Using directory name as deployment name: {name}[/dim]")
    
    console.print(f"\n[bold cyan]🚀 Deploying static files to {platform.capitalize()}...[/bold cyan]\n")
    
    # Validate platform
    platform = platform.lower()
    if platform not in ['vercel', 'netlify']:
        console.print(f"\n[bold red]❌ Platform '{platform}' not supported for static deployment[/bold red]")
        console.print("[yellow]Supported platforms: vercel, netlify[/yellow]\n")
        raise typer.Exit(1)
    
    # Get token
    token_env_vars = {
        'vercel': 'VERCEL_TOKEN',
        'netlify': 'NETLIFY_TOKEN'
    }
    
    token_urls = {
        'vercel': 'https://vercel.com/account/settings/tokens',
        'netlify': 'https://app.netlify.com/user/applications/personal'
    }
    
    env_var = token_env_vars.get(platform)
    token = os.getenv(env_var)
    
    if not token:
        console.print(f"[yellow]⚠️  {env_var} not found in environment[/yellow]")
        console.print(f"[cyan]Get your token from:[/cyan] {token_urls.get(platform)}\n")
        
        token = Prompt.ask(f"Enter your {platform.capitalize()} API token", password=True)
        
        if not token:
            console.print("\n[bold red]❌ Token is required[/bold red]\n")
            raise typer.Exit(1)
    
    # Initialize handler
    handlers = {
        'vercel': VercelHandler,
        'netlify': NetlifyHandler
    }
    
    handler = handlers[platform]({'token': token})
    
    # Authenticate
    console.print("[bold cyan]🔐 Authenticating...[/bold cyan]")
    if not handler.authenticate():
        console.print("\n[bold red]❌ Authentication failed[/bold red]")
        console.print("[yellow]Please check your API token[/yellow]\n")
        raise typer.Exit(1)
    
    console.print("[bold green]✅ Authenticated![/bold green]\n")
    
    # Count files
    file_count = sum(1 for f in files_path.rglob('*') if f.is_file() and not f.name.startswith('.'))
    console.print(f"[dim]Found {file_count} file(s) to deploy[/dim]\n")
    
    # Deploy
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"[cyan]Uploading files to {platform.capitalize()}...", total=None)
        
        try:
            result = handler.deploy_static_files(name, str(files_path))
            progress.update(task, completed=True)
        except Exception as e:
            progress.stop()
            console.print(f"\n[bold red]❌ Deployment failed:[/bold red] {e}\n")
            raise typer.Exit(1)
    
    # Display results
    deployment_url = result.get('url')
    if deployment_url and not deployment_url.startswith('http'):
        deployment_url = f"https://{deployment_url}"
    
    console.print(f"\n[bold green]✅ Deployment successful![/bold green]\n")
    
    panel_content = f"""[bold]Deployment ID:[/bold] {result.get('id', 'N/A')}
[bold]Status:[/bold] {result.get('status', 'Unknown')}
[bold]URL:[/bold] {deployment_url or 'Pending...'}

[dim]Your site will be live in a few seconds...[/dim]
    """
    
    console.print(Panel(
        panel_content,
        title="[bold green]🎉 Deployment Complete[/bold green]",
        border_style="green"
    ))
    
    if deployment_url:
        console.print(f"\n[bold cyan]🌐 Visit your site:[/bold cyan] {deployment_url}\n")
