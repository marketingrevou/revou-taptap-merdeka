"""Static file server for the preview harness.

`python3 -m http.server` cannot be used here: it evaluates `os.getcwd()` to build
the default for its `--directory` flag, which happens before argument parsing and
so fails outright when the launcher hands the process a working directory it is
not permitted to stat — passing `--directory` explicitly does not help.

This anchors itself to the project root off `__file__` instead, and takes the port
from $PORT so the harness can assign one (nothing here needs a fixed port).

    python3 tools/serve.py
"""

import http.server
import os
import socketserver
from functools import partial
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).absolute().parent.parent
PORT = int(os.environ.get("PORT", "8123"))


class Server(socketserver.TCPServer):
    allow_reuse_address = True   # otherwise a restart trips over TIME_WAIT


class Handler(http.server.SimpleHTTPRequestHandler):
    """Mirrors the production rewrite so both campaign variants work locally.

    /swe serves the root index.html without changing the URL, so the page still
    reads "swe" off location.pathname while its relative asset URLs resolve from
    the root. See _redirects / vercel.json for the deployed equivalents.
    """

    def _rewrite(self):
        if urlsplit(self.path).path.rstrip("/") == "/swe":
            self.path = "/index.html"

    def do_GET(self):
        self._rewrite()
        super().do_GET()

    def do_HEAD(self):
        self._rewrite()
        super().do_HEAD()


def main() -> None:
    # Fail loudly rather than serving 404s: chdir only needs +x on the directory,
    # so a process that macOS has denied read access to (a launcher without
    # Documents-folder permission, say) would otherwise start clean and then miss
    # every single file.
    try:
        os.listdir(ROOT)
    except OSError as e:
        raise SystemExit(
            f"cannot read {ROOT}: {e}\n"
            "If this is a launcher-spawned process on macOS, grant the app access "
            "under System Settings > Privacy & Security > Files and Folders "
            "(or Full Disk Access)."
        )

    os.chdir(ROOT)
    handler = partial(Handler, directory=str(ROOT))
    with Server(("127.0.0.1", PORT), handler) as httpd:
        print(f"serving {ROOT} on http://localhost:{PORT}", flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
