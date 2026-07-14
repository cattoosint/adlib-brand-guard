# 🛡️ AdLib Brand Guard

**Monitor Meta's Ad Library for scam ads impersonating your brand — and catch the
image-only ones that hide your name in the picture.**

A configurable, self-hostable tool that scans the public
[Meta Ad Library](https://www.facebook.com/ads/library/), flags ads that
impersonate a brand you configure (logo abuse, executive-face "CEO-bait"
deepfakes, lookalike advertiser pages, financial-scam funnels), and surfaces the
findings in a web dashboard with optional Telegram alerts.

---

## ⚠️ Disclaimer — please read

- **This is a defensive, anti-fraud tool.** Its purpose is to help brand-owners
  and security teams **find scam ads impersonating their own brand** so they can
  report them for takedown. Nothing here creates, runs, or promotes ads.
- **It is a heavily stripped-down reference build.** It was distilled from a
  larger production system into a small, brand-agnostic core so it can be shared
  openly. It is **not** the full pipeline — see
  [What the full version adds](#-what-the-full-version-adds).
- **You are encouraged to fork it and rework it for your own brand.** Point the
  `BRAND_*` settings at your brand, drop in your own reference logos/photos, tune
  the detection vocabulary for your vertical, and wire up your own takedown flow.
- **Respect the law and platform terms.** Scraping and automation are subject to
  Meta's Terms of Service and your local laws. Use responsibly, at low volume,
  for your own brand. Provided "as is", no warranty (MIT).

---

## What it does

1. **Scans** the Meta Ad Library for your search terms across the countries you choose.
2. **Classifies** each ad with a two-sided gate — an ad is only flagged when it
   **both looks like your brand** (brand word, matched logo, or an impersonating
   page name) **and carries scam signals** (guaranteed-returns, giveaway lures,
   funnel-to-WhatsApp/Telegram links, executive-face/name bait, …).
3. **Surfaces** the flagged ads in a dashboard — creative thumbnail, why it was
   flagged, severity, and a deep link to the ad in Meta's Ad Library.
4. **Alerts** you on Telegram (optional).

---

## ✨ Features

**In this repo (working):**

- 🔎 **Meta Ad Library scanner** — multi-term, multi-country, active-only or all.
- 🧠 **Two-sided scam gate** — brand-presence **AND** scam-signal co-occurrence
  keeps false positives off legitimate brand ads.
- 🗣️ **Generic, multilingual-friendly scam lexicon** — guaranteed returns,
  giveaway/prize lures, "join our WhatsApp/Telegram group", limited-slots
  urgency, insider-tips, and off-platform funnel links.
- 🖼️ **Image-only detection** — the scams that never write your brand in the text:
  - **Logo match** (pHash) against your reference logos.
  - **Executive-face match** for **CEO-bait deepfakes** — a cheap
    histogram/block-diff match against reference headshots. A face match
    *bypasses the brand-word gate* (deepfakes rarely spell out the brand).
- 🕵️ **Advertiser-page impersonation** — a non-official page named like your
  brand + a finance/advisory descriptor (e.g. "YourBrand Market Insights") is
  flagged on its own.
- 🔗 **Funnel extraction** — surfaces the WhatsApp / Telegram / shortener /
  suspicious-TLD links scam ads use to move victims off-platform.
- 🖥️ **Web dashboard** — configure the brand, upload your reference kit, run
  scans, and review findings, all in the browser.
- 📤 **Optional Telegram alerts** — a card per flagged ad.
- ⚙️ **Everything configurable** — no brand is hard-coded; env vars + a UI-editable
  `config.json`.

---

## 🚀 Quick start

```bash
git clone <your-fork-url> adlib-brand-guard && cd adlib-brand-guard
python -m venv venv && . venv/Scripts/activate      # (Windows)  or: source venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium               # the scraper's browser

cp .env.example .env          # optional — or just configure in the UI
python cli.py serve           # -> http://127.0.0.1:8000
```

Then, in the dashboard:

1. **Brand** — set your brand name, brand tokens, official domains/pages, and any
   executive names to watch for.
2. **Reference kit** — upload clean **logos** and tight **executive face crops**.
3. **Search** — set your search terms + countries.
4. **▶ Run scan** — findings appear below with severity, reasons, and Ad-Library links.

CLI-only (headless, no dashboard):

```bash
python cli.py scan            # writes output/findings.json
```

---

## ⚙️ Configuration

All settings are editable in the dashboard (persisted to `config.json`) or via
`.env` (see [`.env.example`](.env.example)). Highlights:

| Setting | What it does |
|---|---|
| `BRAND_NAME`, `BRAND_TOKENS` | Your brand + the words that identify it in ad text |
| `BRAND_DOMAINS`, `BRAND_OFFICIAL_PAGES` | Legit domains + FB pages to whitelist |
| `EXEC_NAMES` | Executive names (any language) for CEO-bait detection |
| `SEARCH_TERMS`, `SEARCH_COUNTRIES` | What + where to scan in the Ad Library |
| `WEAK_FLAG_THRESHOLD` | How many weak signals (with brand present) trip a flag |
| `LOGO_PHASH_MAX_DIST`, `FACE_MATCH_MIN_SCORE` | Image-match sensitivity |
| `TELEGRAM_*` | Optional alert bot |

### Reference kit

- `refs/logos/` — clean brand marks/wordmarks (upload via the dashboard).
- `refs/faces/` — **tight face crops** of executives (background hurts the match).

Reference images are **git-ignored by default** — bring your own; don't commit them.

---

## 🧩 How it works

```
 Meta Ad Library  ──scrape──►  ads[]  ──classify──►  findings.json  ──►  dashboard / Telegram
   (Playwright)                          │
                                         ├─ text_signals: brand tokens + scam lexicon + funnels + page-impersonation
                                         └─ image_signals: logo pHash + executive-face match  (optional)
```

- `adlibrary.py` — Playwright scraper of the public Ad Library (simplified;
  Meta's DOM changes, so treat the selectors as a starting point).
- `detection/text_signals.py` — the brand + scam lexicon and rules.
- `detection/image_signals.py` — optional logo pHash + executive-face match.
- `detector.py` — combines signals into a verdict + severity + human reasons.
- `scan.py` — orchestration + persistence + notify.
- `webapp.py` + `static/index.html` — the dashboard and JSON API.

---

## 🔌 Extending it — takedown / reporting

This build **detects and surfaces**; it deliberately does **not** ship an
auto-reporting integration (e.g. Meta **Brand Rights Protection**). Reporting is
brand- and account-specific and often needs human approval, so wire up your own:

- `scan.py` already produces structured `findings` — hand the flagged ones to
  your own reporting step (a review queue, a ticket, a submission to Meta's
  Brand Rights Protection portal, an email to your abuse desk, …).
- The optional Telegram notifier (`telegram_notify.py`) is a good template for an
  **approve-then-act** flow: send a card per finding, add approve/whitelist
  buttons, and only act on a human tap.

---

## 🧱 What the full version adds

The production system this was distilled from goes considerably further. If
you're rebuilding for a real brand-protection operation, these are the levers
worth adding (not shipped here):

- **OCR of creatives** (offline) so image-only text ads flag on their body copy.
- **Logo template matching** (`cv2.matchTemplate`, multi-scale) to locate a
  wordmark embedded in a busy creative — stronger than whole-image pHash.
- **Whole-creative template match** (CLIP embeddings) to catch reuse of a known
  scam template even when OCR fails.
- **Robust executive-face recognition** (embeddings, not histogram) for varied
  deepfake renders.
- **Grouped-ad expansion** — Meta collapses "N ads use this creative" into one
  card; expand it to catch every burner sibling.
- **Advertiser profile-picture impersonation** — flag pages whose avatar *is* the
  brand logo (report the page, not just the ad).
- **ML triage** — a shadow classifier over disposition features to rank findings.
- **Evidence caching** — snapshot creative + text + landing URL at scan time
  (scam ads vanish within hours).
- **Automated takedown reporting** — an approve-in-Telegram → file-with-the-platform
  workflow, rate-limited and human-gated.
- **Multi-market / multi-term scheduling**, alerting (email/Slack), a
  whitelist/allow-list, and a self-monitoring heartbeat.

---

## 📁 Project structure

```
adlib-brand-guard/
├── cli.py                 # `serve` (dashboard) | `scan` (headless)
├── webapp.py              # FastAPI: UI + JSON API
├── static/index.html      # dashboard (single file, no build step)
├── config.py              # env defaults + UI-editable settings store
├── adlibrary.py           # Meta Ad Library scraper (Playwright)
├── detector.py            # combine signals -> verdict
├── detection/
│   ├── text_signals.py    # brand + scam lexicon, funnels, page impersonation
│   └── image_signals.py   # logo pHash + executive-face match (optional)
├── scan.py                # orchestrator + persistence + notify
├── telegram_notify.py     # optional alerts
├── refs/{logos,faces}/    # your reference kit (git-ignored)
└── requirements.txt
```

---

## Limitations

- The Ad Library scraper is a **simplified, best-effort** extractor — Meta's DOM
  changes; adapt the selectors in `adlibrary.py` as needed.
- The image signals are **near-duplicate** matchers (pHash / histogram), not full
  computer vision — great for reused logos/photos, weaker on novel renders.
- No auth on the dashboard — run it locally / behind your own network controls.

---

## License

[MIT](LICENSE). Built for defensive brand protection. Fork it, make it yours.
