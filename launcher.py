"""Inicializador do BusGraph usado pelo executável do Windows."""

from __future__ import annotations

import os
from pathlib import Path
import socket
import sys
from threading import Thread
import time
import webbrowser


HOST = "127.0.0.1"


def available_port(preferred=8501):
    """Escolhe a porta padrão ou a próxima porta local disponível."""
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((HOST, port))
            except OSError:
                continue
            return port
    raise RuntimeError("Nenhuma porta local disponível entre 8501 e 8520.")


def open_browser_when_ready(url, port, timeout=45):
    """Abre o endereço somente depois que o servidor começar a responder."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=0.5):
                webbrowser.open(url, new=2)
                return
        except OSError:
            time.sleep(0.25)


def application_root():
    """Retorna a raiz normal ou a pasta temporária criada pelo PyInstaller."""
    bundled = getattr(sys, "_MEIPASS", None)
    return Path(bundled) if bundled else Path(__file__).resolve().parent


def main():
    app_path = application_root() / "app.py"
    if not app_path.is_file():
        raise FileNotFoundError(f"Aplicação não encontrada: {app_path}")

    port = available_port()
    url = f"http://{HOST}:{port}"
    Thread(target=open_browser_when_ready, args=(url, port), daemon=True).start()

    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--global.developmentMode=false",
        "--server.headless=true",
        f"--server.address={HOST}",
        f"--server.port={port}",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    from streamlit.web import cli as streamlit_cli

    print(f"BusGraph iniciado em {url}")
    raise SystemExit(streamlit_cli.main())


if __name__ == "__main__":
    main()
