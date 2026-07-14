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
    // walk up to the card container (a big-enough ancestor)
    let el = n.parentElement, card = null;
    for (let k = 0; k < 12 && el; k++, el = el.parentElement) {
      if ((el.innerText || '').length > 60) { card = el; break; }
    }
    if (!card) continue;
    const text = (card.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 2000);
    // biggest image in the card = the creative
    let img = '', area = 0;
    card.querySelectorAll('img').forEach(im => {
      const a = (im.naturalWidth || im.width || 0) * (im.naturalHeight || im.height || 0);
      if (a > area && im.src && im.src.startsWith('http')) { area = a; img = im.src; }
    });
    // page/advertiser name = first profile link text
    const a = card.querySelector('a[href*="facebook.com"]');
    out.push({ ad_id: id, body: text, image_url: img,
               page_name: a ? (a.innerText || '').trim().slice(0, 120) : '',
               snapshot_url: 'https://www.facebook.com/ads/library/?id=' + id });
  }
  return out;
}
"""


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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=cfg.HEADLESS)
        page = browser.new_page(viewport={"width": 1400, "height": 1000})
        for term in cfg.SEARCH_TERMS:
            for country in cfg.SEARCH_COUNTRIES:
                url = _LIB_URL.format(status=status, country=country,
                                      q=re.sub(r"\s+", "%20", term))
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(4000)
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
