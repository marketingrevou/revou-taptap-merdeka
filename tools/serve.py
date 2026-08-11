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

ROOT = Path(__file__).absolute().parent.parent
PORT = int(os.environ.get("PORT", "8123"))


class Server(socketserver.TCPServer):
    allow_reuse_address = True   # otherwise a restart trips over TIME_WAIT


def main() -> None:
    os.chdir(ROOT)
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    with Server(("127.0.0.1", PORT), handler) as httpd:
        print(f"serving {ROOT} on http://localhost:{PORT}", flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
