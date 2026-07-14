"""Settings store — brand config editable from the web UI (config.json), with
env vars as the initial defaults. Nothing brand-specific is hard-coded.

The detection modules take a `Settings` object exposing UPPERCASE attributes;
the web UI reads/writes the lowercase dict in config.json.
"""
from __future__ import annotations

import json
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

CONFIG_FILE = os.environ.get("CONFIG_FILE", "config.json")


def _csv(name: str, default: str = "") -> list[str]:
    return [x.strip() for x in os.environ.get(name, default).split(",") if x.strip()]


# Initial defaults from env (first run, before config.json exists).
DEFAULTS: dict = {
    "brand_name": os.environ.get("BRAND_NAME", "ExampleBrand"),
    "brand_tokens": _csv("BRAND_TOKENS", "examplebrand"),
    "brand_domains": _csv("BRAND_DOMAINS", "example.com"),
    "official_pages": _csv("BRAND_OFFICIAL_PAGES"),
    "exec_names": _csv("EXEC_NAMES"),
    "search_terms": _csv("SEARCH_TERMS", os.environ.get("BRAND_NAME", "ExampleBrand")),
    "search_countries": _csv("SEARCH_COUNTRIES", "US"),
    "active_only": (os.environ.get("SEARCH_ACTIVE_ONLY", "1") == "1"),
    "max_ads": int(os.environ.get("MAX_ADS", "200") or 200),
    "scroll_passes": int(os.environ.get("SCROLL_PASSES", "8") or 8),
    "headless": (os.environ.get("HEADLESS", "1") == "1"),
    "weak_flag_threshold": int(os.environ.get("WEAK_FLAG_THRESHOLD", "3") or 3),
    "logo_match_enabled": (os.environ.get("LOGO_MATCH_ENABLED", "1") == "1"),
    "face_match_enabled": (os.environ.get("FACE_MATCH_ENABLED", "1") == "1"),
    "logo_phash_max_dist": int(os.environ.get("LOGO_PHASH_MAX_DIST", "10") or 10),
    "face_match_min_score": float(os.environ.get("FACE_MATCH_MIN_SCORE", "0.82") or 0.82),
    "telegram_enabled": (os.environ.get("TELEGRAM_ENABLED", "0") == "1"),
    "telegram_bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
    "telegram_chat_id": os.environ.get("TELEGRAM_CHAT_ID", ""),
}

LOGO_REF_DIR = os.environ.get("LOGO_REF_DIR", "refs/logos")
FACE_REF_DIR = os.environ.get("FACE_REF_DIR", "refs/faces")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "output")


def load() -> dict:
    """Merged config: DEFAULTS overlaid with whatever the UI saved."""
    data = dict(DEFAULTS)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                data.update({k: v for k, v in json.load(f).items() if k in DEFAULTS})
        except Exception:
            pass
    return data


def save(data: dict) -> dict:
    merged = load()
    merged.update({k: v for k, v in (data or {}).items() if k in DEFAULTS})
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    return merged


class Settings:
    """UPPERCASE view of the config for the detection/fetch modules."""

    def __init__(self, data: dict | None = None):
        d = data or load()
        self.BRAND_NAME = d["brand_name"]
        self.BRAND_TOKENS = [t.lower() for t in d["brand_tokens"]]
        self.BRAND_DOMAINS = [x.lower() for x in d["brand_domains"]]
        self.BRAND_OFFICIAL_PAGES = [p.lower() for p in d["official_pages"]]
        self.EXEC_NAMES = [n.lower() for n in d["exec_names"]]
        self.SEARCH_TERMS = d["search_terms"] or [d["brand_name"]]
        self.SEARCH_COUNTRIES = d["search_countries"] or ["US"]
        self.SEARCH_ACTIVE_ONLY = bool(d["active_only"])
        self.MAX_ADS = int(d["max_ads"])
        self.SCROLL_PASSES = int(d["scroll_passes"])
        self.HEADLESS = bool(d["headless"])
        self.WEAK_FLAG_THRESHOLD = int(d["weak_flag_threshold"])
        self.LOGO_MATCH_ENABLED = bool(d["logo_match_enabled"])
        self.FACE_MATCH_ENABLED = bool(d["face_match_enabled"])
        self.LOGO_PHASH_MAX_DIST = int(d["logo_phash_max_dist"])
        self.FACE_MATCH_MIN_SCORE = float(d["face_match_min_score"])
        self.LOGO_REF_DIR = LOGO_REF_DIR
        self.FACE_REF_DIR = FACE_REF_DIR
        self.TELEGRAM_ENABLED = bool(d["telegram_enabled"])
        self.TELEGRAM_BOT_TOKEN = d["telegram_bot_token"]
        self.TELEGRAM_CHAT_ID = d["telegram_chat_id"]


def settings() -> Settings:
    return Settings(load())
