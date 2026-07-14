"""Combine text + image signals into a verdict for one ad.

Decision logic (all thresholds configurable):
  * brand present  = brand token in text  OR logo match  OR page impersonation
  * exec-bait      = an executive name in text  OR a matched executive face
  * FLAG when:
      - the page name impersonates the brand (strong on its own), OR
      - brand present AND (a strong scam signal OR a funnel link), OR
      - brand present AND >= WEAK_FLAG_THRESHOLD weak signals, OR
      - exec-bait AND any scam signal   (CEO deepfakes rarely say the brand in
        text, so exec-bait bypasses the strict brand-word gate)
"""
from __future__ import annotations

from detection import analyze_text, match_logo, match_face


def classify(ad: dict, cfg) -> dict:
    """`ad`: {ad_id, page_name, body, ocr_text, image_path, links}. Returns a
    verdict dict with flag + human-readable reasons + the raw signals."""
    text = " ".join(x for x in (ad.get("body"), ad.get("ocr_text")) if x)
    ts = analyze_text(text, cfg.BRAND_TOKENS, cfg.BRAND_OFFICIAL_PAGES,
                      cfg.EXEC_NAMES, ad.get("page_name", ""))

    logo = face = None
    img = ad.get("image_path")
    if img:
        if cfg.LOGO_MATCH_ENABLED:
            logo = match_logo(img, cfg.LOGO_REF_DIR, cfg.LOGO_PHASH_MAX_DIST)
        if cfg.FACE_MATCH_ENABLED:
            face = match_face(img, cfg.FACE_REF_DIR, cfg.FACE_MATCH_MIN_SCORE)

    brand_present = ts["has_brand"] or bool(logo) or ts["page_impersonation"]
    exec_bait = bool(ts["exec_hit"]) or bool(face)
    strong = list(ts["strong"]) + [f"funnel:{f}" for f in ts["funnels"]]
    weak = ts["weak"]

    reasons: list[str] = []
    if ts["page_impersonation"]:
        reasons.append(f"page name impersonates {cfg.BRAND_NAME}")
    if logo:
        reasons.append(f"brand logo match ({logo[0]}, dist {logo[1]})")
    if face:
        reasons.append(f"executive face match ({face[0]}, {face[1]:.2f})")
    if ts["exec_hit"]:
        reasons.append(f"executive name in ad: {', '.join(ts['exec_hit'])}")
    if strong:
        reasons.append(f"{len(strong)} strong scam signal(s)")
    if weak:
        reasons.append(f"{len(weak)} weak scam signal(s)")

    flag = bool(
        ts["page_impersonation"]
        or (brand_present and (strong or exec_bait))
        or (brand_present and len(weak) >= cfg.WEAK_FLAG_THRESHOLD)
        or (exec_bait and (strong or weak))
    )

    severity = "low"
    if flag:
        if ts["page_impersonation"] or exec_bait or len(strong) >= 2:
            severity = "high"
        elif strong:
            severity = "medium"

    return {
        "ad_id": ad.get("ad_id"),
        "page_name": ad.get("page_name"),
        "flag": flag,
        "severity": severity,
        "exec_bait": exec_bait,
        "reasons": reasons,
        "snapshot_url": ad.get("snapshot_url"),
        "funnels": ts["funnels"],
        "signals": {"strong": strong, "weak": weak,
                    "brand_present": brand_present,
                    "logo": logo[0] if logo else None,
                    "face": face[0] if face else None},
    }
