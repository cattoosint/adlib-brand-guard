"""Fetch ads from Meta's public Ad Library (https://www.facebook.com/ads/library/).

This is a SIMPLIFIED, best-effort scraper — enough to demonstrate the pipeline
end to end. Meta's Ad Library DOM changes over time, so treat the extraction
selectors as a starting point and adapt them. (A production system would add
retries, rate-limiting, session reuse, grouped-ad expansion, and proxy rotation.)

Requires Playwright:  pip install playwright  &&  python -m playwright install chromium
"""
from __future__ import annotations

import os
import re
import time

_LIB_URL = ("https://www.facebook.com/ads/library/?active_status={status}"
            "&ad_type=all&country={country}&q={q}&media_type=all")

# Pull the ad copy + page name + biggest image out of each Library-ID card.
_EXTRACT_JS = r"""
() => {
  const out = [];
  const seen = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = walker.nextNode())) {
    const m = (n.textContent || '').match(/Library ID:\s*(\d{6,})/i);
    if (!m) continue;
    const id = m[1];
    if (seen.has(id)) continue;
    seen.add(id);
    // walk up until we hit the WHOLE card — an ancestor that has an image or the
    // 'Sponsored' label AND enough text (the metadata-only block is skipped).
    let el = n.parentElement, card = null;
    for (let k = 0; k < 16 && el; k++, el = el.parentElement) {
      const it = el.innerText || '';
      if (it.length > 120 && (el.querySelector('img') || /Sponsored/i.test(it))) {
        card = el;
        if (el.querySelector('img')) break;   // prefer the container that holds the creative
      }
    }
    if (!card) card = n.parentElement;
    const full = (card.innerText || '').replace(/\s+/g, ' ').trim();
    // ad copy = text after the 'Sponsored' label
    const sp = full.search(/\bSponsored\b/i);
    let body = sp >= 0 ? full.slice(sp + 9).trim() : full;
    // advertiser name: prefer a real page link (facebook.com/<page>, not /ads/),
    // rejecting Ad-Library UI chrome text.
    let page = '';
    for (const a of card.querySelectorAll('a[href]')) {
      const href = a.href || '';
      const txt = (a.innerText || '').replace(/​/g, '').trim();
      if (/facebook\.com\/(?!ads\/)/i.test(href) && txt.length >= 2 && txt.length <= 60
          && !/details|drop.?down|versions|library id|sponsored|see |report|active/i.test(txt)) {
        page = txt; break;
      }
    }
    // biggest image in the card = the creative
    let img = '', area = 0;
    card.querySelectorAll('img').forEach(im => {
      const a = (im.naturalWidth || im.width || 0) * (im.naturalHeight || im.height || 0);
      if (a > area && im.src && im.src.startsWith('http')) { area = a; img = im.src; }
    });
    out.push({ ad_id: id, body: body.slice(0, 1600), image_url: img,
               page_name: page.slice(0, 100),
               snapshot_url: 'https://www.facebook.com/ads/library/?id=' + id });
    if (out.length >= 400) break;
  }
  return out;
}
"""


def _dismiss_consent(page) -> None:
    """Best-effort: clear Meta's cookie-consent overlay (privacy-preserving — decline
    optional cookies where offered) so the ad grid can render."""
    for label in ("Decline optional cookies", "Only allow essential cookies",
                  "Allow all cookies", "Allow all", "Accept all"):
        try:
            btn = page.get_by_role("button", name=label)
            if btn.count():
                btn.first.click(timeout=2500)
                page.wait_for_timeout(1200)
                return
        except Exception:
            continue


def _download(page, url: str, dest: str) -> str | None:
    if not url:
        return None
    try:
        resp = page.request.get(url, timeout=15000)
        if resp.ok:
            with open(dest, "wb") as f:
                f.write(resp.body())
            return dest
    except Exception:
        pass
    return None


def fetch_ads(cfg, image_dir: str = "output/images"):
    """Scrape the Ad Library for every SEARCH_TERM x SEARCH_COUNTRY. Returns a
    de-duplicated list of ad dicts: {ad_id, page_name, body, image_url,
    image_path, snapshot_url}. Downloads each creative for the image signals."""
    from playwright.sync_api import sync_playwright

    os.makedirs(image_dir, exist_ok=True)
    status = "active" if cfg.SEARCH_ACTIVE_ONLY else "all"
    ads: dict[str, dict] = {}

    ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    with sync_playwright() as p:
        # ALWAYS headed — Meta serves a degraded (empty) page to headless browsers,
        # so a visible window is required for the ad grid to render. On a headless
        # server, run behind a virtual display (Xvfb). cfg.HEADLESS is ignored here.
        browser = p.chromium.launch(headless=False, args=[
            "--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 1400, "height": 1000}, user_agent=ua)
        for term in cfg.SEARCH_TERMS:
            for country in cfg.SEARCH_COUNTRIES:
                url = _LIB_URL.format(status=status, country=country,
                                      q=re.sub(r"\s+", "%20", term))
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(3000)
                    _dismiss_consent(page)
                    page.wait_for_timeout(2500)
                    for _ in range(cfg.SCROLL_PASSES):
                        page.mouse.wheel(0, 3000)
                        page.wait_for_timeout(800)
                    cards = page.evaluate(_EXTRACT_JS)
                except Exception as exc:
                    print(f"  [warn] {term}/{country}: {type(exc).__name__} — skip")
                    continue
                for c in cards:
                    if c["ad_id"] in ads or len(ads) >= cfg.MAX_ADS:
                        continue
                    dest = os.path.join(image_dir, f"{c['ad_id']}.jpg")
                    c["image_path"] = _download(page, c.get("image_url", ""), dest)
                    ads[c["ad_id"]] = c
                print(f"  {term}/{country}: {len(cards)} cards ({len(ads)} unique so far)")
                if len(ads) >= cfg.MAX_ADS:
                    break
        browser.close()
    return list(ads.values())
