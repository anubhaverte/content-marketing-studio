"""Interactive Layout/Theme Tweak Tool & JSON Spec Editor Launcher.

Launches the visual Card Studio Spec Editor in your default web browser.
Organizers can interactively adjust layout geometry, tweak theme color tokens,
view real-time contrast calculations, inspect print guides (bleed/trim/safe area),
switch between attendee personas, and export custom JSON specs.
"""
from __future__ import annotations

import argparse
import http.server
import os
import socketserver
import sys
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HTML_PATH = REPO_ROOT / "design_tools" / "spec_editor.html"


def launch_browser(serve: bool = False, port: int = 8085) -> None:
    """Launch the interactive spec editor in the default browser."""
    if not HTML_PATH.is_file():
        print(f"Error: Spec editor HTML not found at {HTML_PATH}", file=sys.stderr)
        sys.exit(1)

    if serve:
        os.chdir(str(REPO_ROOT))
        handler = http.server.SimpleHTTPRequestHandler
        url = f"http://localhost:{port}/design_tools/spec_editor.html"
        print(f"\n============================================================")
        print(f"  Card Studio — Interactive Spec & Theme Tweak Tool")
        print(f"  Serving at: {url}")
        print(f"  Press Ctrl+C to stop.")
        print(f"============================================================\n")
        webbrowser.open(url)
        with socketserver.TCPServer(("", port), handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nServer stopped.")
    else:
        file_url = HTML_PATH.as_uri()
        print(f"\n============================================================")
        print(f"  Card Studio — Interactive Spec & Theme Tweak Tool")
        print(f"  Opening: {file_url}")
        print(f"============================================================\n")
        webbrowser.open(file_url)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Launch the interactive layout/theme tweak tool and JSON spec editor."
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start a local HTTP server instead of opening as file URI",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8085,
        help="Port to use when running with --serve (default: 8085)",
    )
    args = parser.parse_args()
    launch_browser(serve=args.serve, port=args.port)


if __name__ == "__main__":
    main()
