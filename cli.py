"""Entry point.

    python cli.py serve     # launch the web dashboard (default)  -> :8000
    python cli.py scan      # run one headless scan from the CLI
"""
import os
import sys


def main():
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "serve").lower()
    if cmd == "scan":
        import scan
        print("Scanning Meta Ad Library …")
        print(scan.run_scan())
    elif cmd == "serve":
        import uvicorn
        import webapp
        host = os.environ.get("HOST", "127.0.0.1")
        port = int(os.environ.get("PORT", "8000"))
        print(f"AdLib Brand Guard → http://{host}:{port}")
        uvicorn.run(webapp.app, host=host, port=port)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
