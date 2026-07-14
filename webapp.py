"""Web dashboard — configure the brand, upload reference logos/faces, run a scan,
and browse findings. Optional Telegram alerts.

    pip install -r requirements.txt
    python -m playwright install chromium
    python webapp.py            # -> http://127.0.0.1:8000
"""
from __future__ import annotations

import os
import threading

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import config
import scan as scanner
from detection import reload_refs

app = FastAPI(title="AdLib Brand Guard")

_REF_DIRS = {"logos": config.LOGO_REF_DIR, "faces": config.FACE_REF_DIR}
_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
for d in (*_REF_DIRS.values(), os.path.join(config.OUTPUT_DIR, "images")):
    os.makedirs(d, exist_ok=True)


# --- config ---------------------------------------------------------------- #
@app.get("/api/config")
def get_config():
    return config.load()


@app.post("/api/config")
async def set_config(payload: dict):
    return config.save(payload or {})


# --- reference kit (logos / executive faces) ------------------------------- #
@app.get("/api/refs/{kind}")
def list_refs(kind: str):
    d = _REF_DIRS.get(kind)
    if not d:
        raise HTTPException(404, "unknown kind")
    return [f for f in sorted(os.listdir(d)) if f.lower().endswith(_EXTS)]


@app.post("/api/refs/{kind}")
async def upload_ref(kind: str, file: UploadFile = File(...)):
    d = _REF_DIRS.get(kind)
    if not d:
        raise HTTPException(404, "unknown kind")
    name = os.path.basename(file.filename or "")
    if not name.lower().endswith(_EXTS):
        raise HTTPException(400, "image files only (.png/.jpg/.webp)")
    with open(os.path.join(d, name), "wb") as f:
        f.write(await file.read())
    reload_refs()
    return {"ok": True, "name": name}


@app.delete("/api/refs/{kind}/{name}")
def delete_ref(kind: str, name: str):
    d = _REF_DIRS.get(kind)
    if not d:
        raise HTTPException(404, "unknown kind")
    p = os.path.join(d, os.path.basename(name))
    if os.path.exists(p):
        os.remove(p)
        reload_refs()
    return {"ok": True}


@app.get("/api/refs/{kind}/{name}")
def get_ref(kind: str, name: str):
    d = _REF_DIRS.get(kind)
    p = os.path.join(d or "", os.path.basename(name))
    if not d or not os.path.exists(p):
        raise HTTPException(404, "not found")
    return FileResponse(p)


# --- scan + findings ------------------------------------------------------- #
@app.post("/api/scan")
def start_scan():
    if scanner.state()["running"]:
        return JSONResponse({"error": "a scan is already running"}, status_code=409)
    threading.Thread(target=scanner.run_scan, daemon=True).start()
    return {"ok": True}


@app.get("/api/scan/state")
def scan_state():
    return scanner.state()


@app.get("/api/findings")
def findings():
    return scanner.load_findings()


@app.get("/api/image")
def image(ad_id: str):
    p = os.path.join(config.OUTPUT_DIR, "images", f"{os.path.basename(ad_id)}.jpg")
    if os.path.exists(p):
        return FileResponse(p)
    raise HTTPException(404, "no image")


# --- telegram test --------------------------------------------------------- #
@app.post("/api/telegram/test")
def telegram_test():
    import telegram_notify
    s = config.settings()
    ok = telegram_notify.send_text(s, "✅ AdLib Brand Guard — Telegram is connected.")
    return {"ok": ok}


# --- static UI (mounted last so /api/* wins) ------------------------------- #
app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("HOST", "127.0.0.1"),
                port=int(os.environ.get("PORT", "8000")))
