"""Inicializador do BusGraph usado pelo executável do Windows."""

from __future__ import annotations

import os
from pathlib import Path
import sys


def application_root():
    """Retorna a raiz normal ou a pasta temporária criada pelo PyInstaller."""
    bundled = getattr(sys, "_MEIPASS", None)
    return Path(bundled) if bundled else Path(__file__).resolve().parent


def main():
    app_path = application_root() / "app.py"
    if not app_path.is_file():
        raise FileNotFoundError(f"Aplicação não encontrada: {app_path}")

    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.headless=false",
        "--browser.gatherUsageStats=false",
    ]
    from streamlit.web import cli as streamlit_cli

    raise SystemExit(streamlit_cli.main())


if __name__ == "__main__":
    main()
