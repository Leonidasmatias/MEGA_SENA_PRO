from __future__ import annotations

from pathlib import Path
import os
import sys
import threading
import time
import webbrowser

from streamlit.web import cli as streamlit_cli


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _localizar_app() -> Path:
    base = _base_dir()
    candidatos = [
        base / "app.py",
        base.parent / "app.py",
        Path.cwd() / "app.py",
    ]
    for candidato in candidatos:
        if candidato.exists():
            return candidato
    raise FileNotFoundError("app.py nao encontrado ao lado do executavel nem na pasta do projeto.")


def _abrir_navegador() -> None:
    time.sleep(4)
    webbrowser.open("http://localhost:8501")


def main() -> None:
    app_path = _localizar_app()
    os.chdir(app_path.parent)
    threading.Thread(target=_abrir_navegador, daemon=True).start()
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        "8501",
        "--server.headless",
        "true",
    ]
    streamlit_cli.main()


if __name__ == "__main__":
    main()
