"""Gera ``dist/BusGraph.exe`` no Windows usando PyInstaller."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "emdec" / "consolidado"


def add_data(source, destination):
    separator = ";" if sys.platform == "win32" else ":"
    return f"{source}{separator}{destination}"


def main():
    if sys.platform != "win32":
        raise SystemExit("O executável .exe deve ser gerado no Windows.")
    if importlib.util.find_spec("PyInstaller") is None:
        raise SystemExit(
            "PyInstaller não encontrado. Execute primeiro: "
            "python -m pip install -r requirements-build.txt"
        )

    required = [
        ROOT / "app.py",
        DATASET / "paradas.csv",
        DATASET / "trechos.csv",
        DATASET / "relatorio.json",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Arquivos obrigatórios ausentes:\n" + "\n".join(missing))

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        "BusGraph",
        "--collect-all",
        "streamlit",
        "--collect-all",
        "folium",
        "--collect-all",
        "branca",
        "--hidden-import",
        "data.local_loader",
        "--hidden-import",
        "services.ida_view",
        "--hidden-import",
        "services.road_router",
        "--hidden-import",
        "services.weighted_routes",
        "--add-data",
        add_data(ROOT / "app.py", "."),
        "--add-data",
        add_data(DATASET / "paradas.csv", "datasets/emdec/consolidado"),
        "--add-data",
        add_data(DATASET / "trechos.csv", "datasets/emdec/consolidado"),
        "--add-data",
        add_data(DATASET / "relatorio.json", "datasets/emdec/consolidado"),
        str(ROOT / "launcher.py"),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    print(f"\nExecutável gerado em: {ROOT / 'dist' / 'BusGraph.exe'}")


if __name__ == "__main__":
    main()
