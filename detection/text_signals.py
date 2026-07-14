"""Text-based scam signals.

The gate is deliberately two-sided: an ad is only flagged when it BOTH looks
like the brand (a brand token / lookalike page) AND carries scam vocabulary.
That co-occurrence is what keeps false positives down on legitimate brand ads.

None of the vocabulary here is brand-specific — it's the generic financial-scam
lexicon (guaranteed returns, giveaway lures, funnel-to-WhatsApp, etc.). Tune it
for your vertical.
"""
from __future__ import annotations

import re

# --- generic scam vocabulary ------------------------------------------------
# STRONG: on its own, strong evidence of a scam funnel.
_STRONG = [
    r"guaranteed (returns?|profit|income)",
    r"risk[- ]?free (returns?|profit|investment)",
    r"\d{2,3}\s*%\s*(daily|weekly|monthly|guaranteed)?\s*(returns?|profit|roi)",
    r"double your (money|investment|capital)",
    r"(join|add|dm|message).{0,20}(whatsapp|telegram|wechat) (group|now|channel)",
    r"(free|exclusive|limited).{0,20}(investment|trading|stock|crypto) (course|class|masterclass|signal)",
    r"claim (your|them|now).{0,20}(free )?(stocks?|shares?|bonus|reward|package)",
    r"congratulations.{0,40}(qualified|selected|eligible|won).{0,20}(stocks?|shares?|premium|investment|prize|reward)",
    r"\d[\d,]{2,}\s*exclusive (investment|trading) packages?",
    r"limited (slots?|spots?|places?).{0,20}(join|register|apply) (now|today)",
]
# WEAK: individually ambiguous; several together are suspicious.
_WEAK = [
    r"\bpassive income\b", r"\bfinancial freedom\b", r"\bside income\b",
    r"\bwealth (growth|building)\b", r"\bmarket (alert|insights?|movers?)\b",
    r"\bhot stocks?\b", r"\bpenny stocks?\b", r"\binsider (tips?|info)\b",
    r"\binvestment (course|class|group|community)\b",
    r"\bjoin (our|the) (group|community|channel)\b",
    r"\bfree (community|training|webinar|seminar)\b",
    r"\bno (experience|fee|sales)\b", r"\bzero fee\b",
    r"\bact (now|fast)\b", r"\bdon'?t miss\b", r"\bhurry\b",
    r"\bclick (the )?link\b", r"\bregister (now|today)\b",
]
_STRONG_RE = [re.compile(p, re.I) for p in _STRONG]
_WEAK_RE = [re.compile(p, re.I) for p in _WEAK]

# funnel destinations that scam ads use to move victims off-platform
_FUNNEL_RE = re.compile(
    r"(https?://)?(wa\.me/|t\.me/|bit\.ly/|tinyurl\.com/|cutt\.ly/|[a-z0-9-]+\.(?:icu|xyz|top|click|live|vip|link|online|site))",
    re.I,
)
# advisory/finance descriptors used in lookalike PAGE names ("<Brand> Insights")
_PAGE_IMPERSONATION_DESC = re.compile(
    r"\b(insights?|market|trading|stocks?|invest(?:ment)?|academy|signals?|"
    r"course|fx|forex|crypto|capital|advisory|wealth|education)\b", re.I)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def analyze_text(text: str, brand_tokens: list[str], official_pages: list[str],
                 exec_names: list[str] | None = None, page_name: str = ""):
    """Return a dict of text signals for one ad. `text` = ad body + any OCR."""
    t = _norm(text).lower()
    pn = _norm(page_name).lower()
    exec_names = exec_names or []

    has_brand = any(tok in t for tok in brand_tokens)
    strong = [r.pattern for r in _STRONG_RE if r.search(t)]
    weak = [r.pattern for r in _WEAK_RE if r.search(t)]
    funnels = sorted({m.group(0).rstrip(".,) ") for m in _FUNNEL_RE.finditer(text or "")})
    exec_hit = [n for n in exec_names if n and n in t]

    # lookalike page: a NON-official page whose NAME contains a brand token AND a
    # finance/advisory descriptor → impersonation (strong on its own).
    page_impersonation = bool(
        pn and pn not in official_pages
        and any(tok in pn for tok in brand_tokens)
        and _PAGE_IMPERSONATION_DESC.search(pn))

    return {
        "has_brand": has_brand,
        "strong": strong,
        "weak": weak,
        "funnels": funnels,
        "exec_hit": exec_hit,
        "page_impersonation": page_impersonation,
    }
