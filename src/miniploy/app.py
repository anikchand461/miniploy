import typer
from miniploy.commands.deploy import deploy
from miniploy.commands.setup import setup
from miniploy.commands.run import run
from miniploy.commands.tokens import tokens
from miniploy.commands.static import static
from miniploy.commands.manage import manage

app = typer.Typer(
    name="miniploy",
    help="One-stop AI-powered deployment to Render, Fly.io, Vercel, Railway, Netlify",
    add_completion=True,
    no_args_is_help=True,
)

app.command(help="Manage API tokens for deployment platforms")(tokens)
app.command(help="Deploy static files (HTML, CSS, JS) directly")(static)
app.command(help="List all deployments across platforms")(manage)
app.command(help="Configure selected platform (AI-assisted)")(setup)
app.command(help="Analyze codebase and prepare deployment config")(deploy)
app.command(help="Deploy to the configured platform")(run)


@app.callback()
def main_callback(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """miniploy - the simplest way to ship your app"""
    if verbose:
        print("[DEBUG] Verbose mode enabled")
    # You can store global state here later (config, logger level, etc.)
