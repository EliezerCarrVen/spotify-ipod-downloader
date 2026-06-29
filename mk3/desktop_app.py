"""Desktop launcher for the mk3 iPod Sync Studio HTML interface.

This entry point is intentionally lightweight so it can be packaged with
PyInstaller while the current Python sync backend is migrated behind the UI.
"""

from __future__ import annotations

import os
import sys
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_NAME = "iPod Sync Studio mk3"
HOST = "127.0.0.1"
PORT = int(os.getenv("IPOD_SYNC_STUDIO_PORT", "8765"))


def resource_path(relative_path: str) -> Path:
    """Return a resource path that works both in source and PyInstaller builds."""
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / relative_path


class QuietHandler(SimpleHTTPRequestHandler):
    """HTTP handler with minimal console noise for desktop usage."""

    def log_message(self, format: str, *args: object) -> None:
        return


def build_server(ui_dir: Path) -> ThreadingHTTPServer:
    """Create a local static-file server rooted at the bundled UI folder."""

    class UIHandler(QuietHandler):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, directory=str(ui_dir), **kwargs)

    return ThreadingHTTPServer((HOST, PORT), UIHandler)


def main() -> None:
    """Launch the mk3 desktop UI in the user's default browser."""
    ui_dir = resource_path("ui")
    index_path = ui_dir / "ipod_sync_studio_mk3_desktop_preview.html"

    if not index_path.exists():
        raise FileNotFoundError(f"No se encontró la interfaz HTML: {index_path}")

    server = build_server(ui_dir)
    url = f"http://{HOST}:{PORT}/{index_path.name}"
    print(f"{APP_NAME} iniciado en {url}", flush=True)
    print("Cierra esta ventana para detener el servidor local.", flush=True)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    webbrowser.open(url)

    try:
        thread.join()
    except KeyboardInterrupt:
        print("\nCerrando iPod Sync Studio mk3...")
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
