"""MCP Server CyberThreats package."""


def run_app() -> None:
    """Launch the Streamlit front-end.

    Console-script entry point — invoked by the ``mcp-server-cyberthreats`` command
    installed with the package.  Any extra CLI arguments are passed through
    to Streamlit (e.g. ``mcp-server-cyberthreats --server.port 8502``).
    """
    import subprocess
    import sys
    from pathlib import Path

    app = Path(__file__).parent / "app" / "ui.py"
    sys.exit(subprocess.call([sys.executable, "-m", "streamlit", "run", str(app)] + sys.argv[1:]))
