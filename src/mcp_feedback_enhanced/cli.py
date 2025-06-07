"""
MCP Feedback Enhanced CLI

Command-line interface for the MCP Feedback Enhanced system.
Supports uvx one-click usage and traditional installation.
"""

import typer
from typing import Optional
import uvicorn
import sys
import os
from pathlib import Path

# Import version from package
try:
    from . import __version__
except ImportError:
    __version__ = "0.1.0"

# Import build utilities
try:
    from .utils.build_utils import (
        ensure_frontend_built,
        clean_frontend_build,
        get_frontend_stats,
        format_file_size,
        check_node_environment
    )
except ImportError:
    # Fallback functions if build_utils is not available
    def ensure_frontend_built(*args, **kwargs):
        return True
    def clean_frontend_build():
        return True
    def get_frontend_stats():
        return {}
    def format_file_size(size):
        return f"{size} bytes"
    def check_node_environment():
        return {}

app = typer.Typer(
    name="mcp-feedback-enhanced",
    help="🎯 MCP Feedback Enhanced - Modern feedback collection system",
    add_completion=False,
    rich_markup_mode="rich"
)


@app.command()
def serve(
    host: str = typer.Option(
        "127.0.0.1",
        "--host", "-h",
        help="Host to bind the server to"
    ),
    port: int = typer.Option(
        8000,
        "--port", "-p",
        help="Port to bind the server to"
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Enable auto-reload for development"
    ),
    workers: int = typer.Option(
        1,
        "--workers", "-w",
        help="Number of worker processes"
    ),
    log_level: str = typer.Option(
        "info",
        "--log-level",
        help="Log level (debug, info, warning, error, critical)"
    )
):
    """
    🚀 Start the MCP Feedback Enhanced server
    
    This command starts the FastAPI server with the Vue.js frontend
    and MCP protocol support.
    """
    typer.echo(f"🎯 Starting MCP Feedback Enhanced v{__version__}")
    typer.echo(f"🌐 Server will be available at: http://{host}:{port}")
    typer.echo(f"📚 API Documentation: http://{host}:{port}/docs")
    typer.echo(f"🔧 Workers: {workers}, Log Level: {log_level}")

    if reload:
        typer.echo("⚠️  Auto-reload enabled (development mode)")

    # 檢查前端構建
    typer.echo("🔍 檢查前端構建...")
    if not ensure_frontend_built(verbose=False):
        typer.echo("⚠️  前端未構建，將以 API 模式運行")
        typer.echo("💡 使用 'mcp-feedback-enhanced build' 命令構建前端")
    else:
        typer.echo("✅ 前端已準備就緒")

    try:
        # Import the FastAPI app
        from .backend.main import app as fastapi_app
        
        # Start the server
        uvicorn.run(
            "mcp_feedback_enhanced.backend.main:app",
            host=host,
            port=port,
            reload=reload,
            workers=workers if not reload else 1,  # reload doesn't work with multiple workers
            log_level=log_level,
            access_log=True
        )
    except ImportError as e:
        typer.echo(f"❌ Error importing FastAPI app: {e}", err=True)
        typer.echo("💡 Make sure all dependencies are installed", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Error starting server: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def version():
    """
    📋 Show version information
    """
    typer.echo(f"MCP Feedback Enhanced v{__version__}")
    typer.echo("Built with FastAPI + Vue.js 3 + WebSocket")
    typer.echo("Repository: https://github.com/Minidoracat/mcp-feedback-enhanced")


@app.command()
def build(
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="Force rebuild even if frontend already exists"
    ),
    clean: bool = typer.Option(
        False,
        "--clean", "-c",
        help="Clean build artifacts before building"
    ),
    verbose: bool = typer.Option(
        True,
        "--verbose/--quiet", "-v/-q",
        help="Show detailed build output"
    )
):
    """
    🔨 Build the frontend application

    This command builds the Vue.js frontend and integrates it with the backend.
    """
    typer.echo("🔨 Building MCP Feedback Enhanced Frontend")

    if clean:
        typer.echo("🧹 Cleaning previous build...")
        if clean_frontend_build():
            typer.echo("✅ Build artifacts cleaned")
        else:
            typer.echo("❌ Failed to clean build artifacts", err=True)
            raise typer.Exit(1)

    # 檢查 Node.js 環境
    env_info = check_node_environment()
    if not env_info.get("node_available"):
        typer.echo("❌ Node.js not found. Please install Node.js to build the frontend.", err=True)
        typer.echo("💡 Download from: https://nodejs.org/", err=True)
        raise typer.Exit(1)

    if not env_info.get("npm_available"):
        typer.echo("❌ npm not found. Please install npm to build the frontend.", err=True)
        raise typer.Exit(1)

    if verbose:
        typer.echo(f"✅ Node.js {env_info.get('node_version', 'unknown')}")
        typer.echo(f"✅ npm {env_info.get('npm_version', 'unknown')}")

    # 執行構建
    typer.echo("🚀 Starting frontend build...")
    if ensure_frontend_built(force_rebuild=force, verbose=verbose):
        typer.echo("🎉 Frontend build completed successfully!")

        # 顯示構建統計
        stats = get_frontend_stats()
        typer.echo(f"📊 Build Stats:")
        typer.echo(f"   Files: {stats.get('file_count', 0)}")
        typer.echo(f"   Size: {format_file_size(stats.get('total_size', 0))}")

        build_info = stats.get('build_info', {})
        if build_info:
            typer.echo(f"   Build Time: {build_info.get('build_time', 'unknown')}")
            typer.echo(f"   Duration: {build_info.get('build_duration', 0):.2f}s")
    else:
        typer.echo("❌ Frontend build failed!", err=True)
        typer.echo("💡 Check the error messages above for details", err=True)
        raise typer.Exit(1)


@app.command()
def info():
    """
    ℹ️  Show system information and configuration
    """
    typer.echo("🎯 MCP Feedback Enhanced System Information")
    typer.echo(f"Version: {__version__}")
    typer.echo(f"Python: {sys.version}")
    typer.echo(f"Platform: {sys.platform}")

    # Check if running in development mode
    package_path = Path(__file__).parent
    typer.echo(f"Package Path: {package_path}")

    # Frontend information
    typer.echo("\n🎨 Frontend Information:")
    stats = get_frontend_stats()
    if stats.get("frontend_built"):
        typer.echo("✅ Frontend build found")
        typer.echo(f"   Files: {stats.get('file_count', 0)}")
        typer.echo(f"   Size: {format_file_size(stats.get('total_size', 0))}")

        build_info = stats.get('build_info', {})
        if build_info:
            typer.echo(f"   Build Time: {build_info.get('build_time', 'unknown')}")
            typer.echo(f"   Node Version: {build_info.get('node_version', 'unknown')}")
            typer.echo(f"   npm Version: {build_info.get('npm_version', 'unknown')}")
    else:
        typer.echo("⚠️  Frontend build not found")
        typer.echo("💡 Run 'mcp-feedback-enhanced build' to build the frontend")

    # Node.js environment
    typer.echo("\n🟢 Node.js Environment:")
    env_info = check_node_environment()
    if env_info.get("node_available"):
        typer.echo(f"✅ Node.js {env_info.get('node_version', 'unknown')}")
    else:
        typer.echo("❌ Node.js not found")

    if env_info.get("npm_available"):
        typer.echo(f"✅ npm {env_info.get('npm_version', 'unknown')}")
    else:
        typer.echo("❌ npm not found")

    if env_info.get("frontend_dir_exists"):
        typer.echo("✅ Frontend directory exists")
    else:
        typer.echo("❌ Frontend directory not found")

    if env_info.get("package_json_exists"):
        typer.echo("✅ package.json found")
    else:
        typer.echo("❌ package.json not found")

    # Environment variables
    typer.echo("\n🔧 Environment Configuration:")
    env_vars = [
        "MCP_FEEDBACK_HOST",
        "MCP_FEEDBACK_PORT",
        "MCP_FEEDBACK_SESSION_TIMEOUT",
        "MCP_FEEDBACK_MAX_FILE_SIZE",
        "ENVIRONMENT"
    ]

    for var in env_vars:
        value = os.getenv(var, "Not set")
        typer.echo(f"  {var}: {value}")


def main():
    """
    Main entry point for the CLI application.
    This function is called when the package is executed with uvx or pip.
    """
    app()


if __name__ == "__main__":
    main()
