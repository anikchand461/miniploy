"""Tokens command - Manage API tokens for deployment platforms."""
import os
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from dotenv import dotenv_values, set_key

console = Console()

PLATFORMS = {
    'vercel': {
        'url': 'https://vercel.com/account/settings/tokens',
        'env_var': 'VERCEL_TOKEN',
        'description': 'Vercel - Next.js, React, Static Sites'
    },
    'netlify': {
        'url': 'https://app.netlify.com/user/applications/personal',
        'env_var': 'NETLIFY_TOKEN',
        'description': 'Netlify - JAMstack, Static Sites'
    },
    'render': {
        'url': 'https://dashboard.render.com/u/settings?add-api-key',
        'env_var': 'RENDER_TOKEN',
        'description': 'Render - Full-stack, Docker, Web Services'
    },
    'railway': {
        'url': 'https://railway.com/account/tokens',
        'env_var': 'RAILWAY_TOKEN',
        'description': 'Railway - Databases, Backend Services'
    },
    'flyio': {
        'url': 'https://fly.io/user/personal_access_tokens',
        'env_var': 'FLY_API_TOKEN',
        'description': 'Fly.io - Containers, Global Apps'
    }
}


def get_env_file() -> Path:
    """Get or create .env file path."""
    env_file = Path.cwd() / '.env'
    if not env_file.exists():
        env_file.touch()
    return env_file


def tokens(
    platform: str = typer.Argument(None, help="Platform: vercel | netlify | render | railway | flyio | all"),
):
    """
    Manage API tokens for deployment platforms.
    
    Add or update tokens for the platforms you want to use.
    Tokens are saved to .env file for security.
    """
    
    if not platform:
        show_tokens_menu()
        return
    
    platform = platform.lower()
    
    if platform == 'all':
        add_all_tokens()
    elif platform in PLATFORMS:
        add_single_token(platform)
    else:
        console.print(f"\n[bold red]❌ Unknown platform:[/bold red] {platform}")
        console.print(f"[yellow]Supported:[/yellow] {', '.join(PLATFORMS.keys())}, all\n")
        raise typer.Exit(1)


def show_tokens_menu():
    """Show interactive menu to manage tokens."""
    console.print("\n[bold cyan]🔐 API Token Manager[/bold cyan]\n")
    
    env_file = get_env_file()
    current_tokens = dotenv_values(env_file)
    
    # Show current status
    console.print("[bold yellow]📌 Current Token Status:[/bold yellow]\n")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Platform", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Get Token", style="green")
    
    for platform, info in PLATFORMS.items():
        has_token = current_tokens.get(info['env_var']) is not None
        status = "[bold green]✓ Set[/bold green]" if has_token else "[bold red]✗ Not Set[/bold red]"
        table.add_row(platform.capitalize(), status, info['url'])
    
    console.print(table)
    
    console.print("\n[bold cyan]📋 Options:[/bold cyan]")
    console.print("  1. Add/update tokens for specific platform")
    console.print("  2. Add tokens for all platforms")
    console.print("  3. View current tokens (masked)")
    console.print("  4. Exit\n")
    
    choice = Prompt.ask("Choose an option", choices=["1", "2", "3", "4"])
    
    if choice == "1":
        console.print()
        for i, platform in enumerate(PLATFORMS.keys(), 1):
            console.print(f"  {i}. {platform.capitalize()}")
        console.print()
        platform_choice = Prompt.ask("Select platform", choices=[str(i) for i in range(1, len(PLATFORMS) + 1)])
        platform = list(PLATFORMS.keys())[int(platform_choice) - 1]
        add_single_token(platform)
    elif choice == "2":
        add_all_tokens()
    elif choice == "3":
        view_tokens()
    # choice == "4" just exits


def add_single_token(platform: str):
    """Add token for a specific platform."""
    if platform not in PLATFORMS:
        console.print(f"\n[bold red]❌ Unknown platform:[/bold red] {platform}\n")
        return
    
    info = PLATFORMS[platform]
    env_file = get_env_file()
    current_tokens = dotenv_values(env_file)
    
    console.print(f"\n[bold cyan]🔐 {platform.capitalize()} Token Setup[/bold cyan]\n")
    console.print(f"[yellow]📌 Get your token from:[/yellow]\n  🔗 {info['url']}\n")
    
    token = Prompt.ask(f"Enter your {platform.capitalize()} API token", password=True)
    
    if not token:
        console.print("[yellow]⏭️  Skipped[/yellow]\n")
        return
    
    # Save to .env
    set_key(str(env_file), info['env_var'], token)
    console.print(f"[bold green]✓ {platform.capitalize()} token saved![/bold green]\n")


def add_all_tokens():
    """Interactively add tokens for all platforms."""
    env_file = get_env_file()
    
    console.print("\n[bold cyan]🔐 Add Tokens for All Platforms[/bold cyan]\n")
    console.print("[dim]Skip any platform by pressing Enter without entering a token[/dim]\n")
    
    for platform, info in PLATFORMS.items():
        console.print(f"[cyan]{platform.capitalize()}[/cyan]")
        console.print(f"  🔗 {info['url']}")
        
        token = Prompt.ask(f"Enter token (or press Enter to skip)", password=True, default="")
        
        if token:
            set_key(str(env_file), info['env_var'], token)
            console.print("[bold green]✓ Saved[/bold green]\n")
        else:
            console.print("[yellow]⏭️  Skipped[/yellow]\n")
    
    console.print("[bold green]✅ Token setup complete![/bold green]\n")


def view_tokens():
    """View current tokens (masked for security)."""
    env_file = get_env_file()
    current_tokens = dotenv_values(env_file)
    
    console.print("\n[bold cyan]🔐 Current Tokens (Masked)[/bold cyan]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Platform", style="cyan")
    table.add_column("Token", style="yellow")
    
    for platform, info in PLATFORMS.items():
        token = current_tokens.get(info['env_var'])
        if token:
            masked = token[:10] + "..." + token[-4:] if len(token) > 14 else "***"
            table.add_row(platform.capitalize(), masked)
        else:
            table.add_row(platform.capitalize(), "[dim]Not set[/dim]")
    
    console.print(table)
    console.print()
