"""Optional Telegram notifier — posts a card per flagged ad to your chat.

Enable it in the web UI (or TELEGRAM_ENABLED=1 + token/chat in .env). Best-effort:
a Telegram hiccup never breaks a scan.
"""
from __future__ import annotations

try:
    import httpx
except Exception:
    httpx = None


def _esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _api(token: str, method: str, **kw):
    if httpx is None or not token:
        return False
    try:
        with httpx.Client(timeout=20.0) as c:
            r = c.post(f"https://api.telegram.org/bot{token}/{method}", json=kw)
        return r.status_code == 200
    except Exception:
        return False


def send_text(settings, text: str) -> bool:
    return _api(settings.TELEGRAM_BOT_TOKEN, "sendMessage",
                chat_id=settings.TELEGRAM_CHAT_ID, text=text[:4000],
                parse_mode="HTML", disable_web_page_preview=True)


def send_findings(settings, flagged: list[dict]) -> None:
    if not (settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID):
        return
    send_text(settings, f"🚨 <b>{len(flagged)}</b> suspected fake "
                        f"{_esc(settings.BRAND_NAME)} ad(s) detected:")
    for f in flagged[:25]:
        lines = [f"🚩 <b>{f['severity'].upper()}</b> — {_esc(f.get('page_name') or 'unknown page')}"]
        if f.get("exec_bait"):
            lines.append("🔴 executive-face / name (deepfake risk)")
        lines.append("Why: " + _esc("; ".join(f.get("reasons", []))[:300]))
        if f.get("snapshot_url"):
            lines.append(f'<a href="{_esc(f["snapshot_url"])}">View in Meta Ad Library</a>')
        send_text(settings, "\n".join(lines))
