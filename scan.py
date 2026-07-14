"""Orchestrator: fetch Ad Library ads -> classify -> persist findings -> notify.

Run it from the CLI (`python cli.py scan`) or trigger it from the web UI.
"""
from __future__ import annotations

import json
import os
import time

import config
from adlibrary import fetch_ads
from detector import classify

_STATE = {"running": False, "last_run": None, "last_error": None,
          "flagged": 0, "scanned": 0}


def state() -> dict:
    return dict(_STATE)


def run_scan(settings=None) -> dict:
    """Fetch + classify + save. Returns a summary; findings land in
    output/findings.json (used by the web UI)."""
    settings = settings or config.settings()
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    _STATE.update(running=True, last_error=None)
    try:
        ads = fetch_ads(settings, image_dir=os.path.join(config.OUTPUT_DIR, "images"))
        findings = []
        for ad in ads:
            v = classify(ad, settings)
            v["body_preview"] = (ad.get("body") or "")[:300]
            v["image_path"] = ad.get("image_path")
            findings.append(v)
        findings.sort(key=lambda f: (not f["flag"],
                                     {"high": 0, "medium": 1, "low": 2}.get(f["severity"], 3)))
        flagged = [f for f in findings if f["flag"]]

        with open(os.path.join(config.OUTPUT_DIR, "findings.json"), "w",
                  encoding="utf-8") as f:
            json.dump({"generated_at": int(time.time()),
                       "scanned": len(findings), "flagged": len(flagged),
                       "findings": findings}, f, indent=2, ensure_ascii=False)

        if settings.TELEGRAM_ENABLED and flagged:
            try:
                import telegram_notify
                telegram_notify.send_findings(settings, flagged)
            except Exception as exc:
                print(f"  [telegram] notify failed: {exc}")

        _STATE.update(scanned=len(findings), flagged=len(flagged),
                      last_run=int(time.time()))
        return {"scanned": len(findings), "flagged": len(flagged)}
    except Exception as exc:
        _STATE["last_error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        _STATE["running"] = False


def load_findings() -> dict:
    path = os.path.join(config.OUTPUT_DIR, "findings.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"generated_at": None, "scanned": 0, "flagged": 0, "findings": []}


if __name__ == "__main__":
    print("Scanning Meta Ad Library ...")
    print(run_scan())
