"""Deploy command - AI-powered project analysis and configuration."""
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
import time

from miniploy.ai.analyzer import analyze_project
from miniploy.config.manager import save_config

console = Console()


def deploy(
    path: str = typer.Argument(".", help="Project directory (default: current)"),
    auto: bool = typer.Option(False, "--auto", "-a", help="Auto-approve AI suggestions"),
    platform: str = typer.Option(None, "--platform", "-p", help="Target platform to optimize for"),
):
    """
    Scan project, detect framework, and let AI suggest deployment configuration.
    
    This command analyzes your codebase and uses AI to suggest the best
    deployment configuration including build commands, environment variables,
    and platform recommendations.
    """
    console.print(f"\n[bold cyan]🔍 Analyzing project at:[/bold cyan] {path}\n")
    
    # Analyze project with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]AI analyzing codebase...", total=None)
        result = analyze_project(path)
        progress.update(task, completed=True)
    
    # Check confidence
    confidence = result.get('confidence', 0.0)
    if confidence < 0.3:
        console.print("[bold red]⚠️  AI confidence is very low. Results may not be accurate.[/bold red]\n")
    elif confidence < 0.6:
        console.print("[bold yellow]⚠️  AI confidence is moderate. Please review suggestions carefully.[/bold yellow]\n")
    
    # Display analysis results
    summary = result.get('summary', 'No summary available')
    framework = result.get('framework', 'unknown')
    runtime = result.get('runtime', 'unknown')
    
    panel_content = f"""[bold]Framework:[/bold] {framework}
[bold]Runtime:[/bold] {runtime}
[bold]Confidence:[/bold] {confidence:.0%}

{summary}
    """
    
    console.print(Panel(
        panel_content,
        title="[bold green]📊 AI Analysis Results[/bold green]",
        border_style="green"
    ))
    
    # Display configuration suggestions
    console.print("\n[bold cyan]⚙️  Suggested Configuration:[/bold cyan]\n")
    
    config_table = Table(show_header=True, header_style="bold magenta")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")
    
    config_table.add_row("Runtime", result.get('runtime', 'unknown'))
    config_table.add_row("Build Command", result.get('build_command', '(none)'))
    config_table.add_row("Start Command", result.get('start_command', '(none)'))
    config_table.add_row("Install Command", result.get('install_command', '(auto-detected)'))
    config_table.add_row("Publish Directory", result.get('publish_dir', '.'))
    
    console.print(config_table)
    
    # Display environment variables if any
    env_vars = result.get('env_vars_needed', [])
    if env_vars:
        console.print(f"\n[bold yellow]🔐 Environment Variables Needed:[/bold yellow]")
        for var in env_vars:
            console.print(f"   • {var}")
    
    # Display platform recommendations
    recommendations = result.get('platform_recommendations', {})
    if recommendations and not platform:
        console.print("\n[bold cyan]🚀 Platform Recommendations:[/bold cyan]\n")
        
        rec_table = Table(show_header=True, header_style="bold magenta")
        rec_table.add_column("Platform", style="cyan")
        rec_table.add_column("Score", justify="center", style="green")
        rec_table.add_column("Reason", style="yellow")
        
        # Sort by score
        sorted_recs = sorted(
            recommendations.items(),
            key=lambda x: x[1].get('score', 0),
            reverse=True
        )
        
        for platform_name, info in sorted_recs:
            score = info.get('score', 0.0)
            reason = info.get('reason', 'N/A')
            rec_table.add_row(
                platform_name.capitalize(),
                f"{score:.0%}",
                reason
            )
        
        console.print(rec_table)
    
    # Confirm and save
    console.print()
    if auto:
        should_save = True
        console.print("[bold green]✓ Auto-mode enabled - saving configuration[/bold green]")
    else:
        should_save = Confirm.ask("💾 Save this configuration to miniploy.yaml?", default=True)
    
    if should_save:
        # Prepare config to save
        config = {
            'framework': framework,
            'runtime': runtime,
            'build_command': result.get('build_command', ''),
            'start_command': result.get('start_command', ''),
            'install_command': result.get('install_command', ''),
            'publish_dir': result.get('publish_dir', '.'),
            'dockerfile': result.get('dockerfile'),
            'project_path': str(Path(path).resolve()),
            'env_vars': {},
            'ai_analysis': {
                'confidence': confidence,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
        }
        
        if platform:
            config['platform'] = platform
        elif recommendations:
            # Use top recommendation
            top_platform = sorted_recs[0][0] if sorted_recs else None
            if top_platform:
                config['platform'] = top_platform
        
        try:
            config_path = save_config(config, None)
            console.print(f"\n[bold green]✅ Configuration saved to {config_path}[/bold green]")
            console.print("\n[dim]Next steps:[/dim]")
            console.print("  1. [cyan]miniploy setup <platform>[/cyan] - Set up your chosen platform")
            console.print("  2. [cyan]miniploy run[/cyan] - Deploy your application")
        except Exception as e:
            console.print(f"\n[bold red]❌ Error saving configuration: {e}[/bold red]")
            raise typer.Exit(1)
    else:
        console.print("\n[yellow]Configuration not saved. Run again when ready.[/yellow]")
