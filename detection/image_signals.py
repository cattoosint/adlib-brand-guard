"""Optional image signals — logo match + executive-face match.

These catch the image-only scams that carry NO brand word in the text: a creative
that pastes the brand logo, or an executive's face onto a fake news chyron.

All of this is best-effort and optional. If Pillow / imagehash / opencv aren't
installed, or no reference images are provided, every function returns "no match"
and the text pipeline still works. Drop reference images into:
    refs/logos/   — clean brand logos/wordmarks (pHash near-duplicate match)
    refs/faces/   — tight face crops of executives (histogram/block-diff match)
"""
from __future__ import annotations

import os

try:
    from PIL import Image
    import imagehash
    _PHASH_OK = True
except Exception:
    _PHASH_OK = False

try:
    import numpy as np
    _NP_OK = True
except Exception:
    _NP_OK = False

_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
_logo_hashes: list[tuple[str, object]] | None = None
_face_prints: list[tuple[str, object]] | None = None


# --------------------------------------------------------------------------- #
#  logo pHash                                                                 #
# --------------------------------------------------------------------------- #
def _load_logo_hashes(ref_dir: str):
    global _logo_hashes
    out: list[tuple[str, object]] = []
    if _PHASH_OK and os.path.isdir(ref_dir):
        for f in sorted(os.listdir(ref_dir)):
            if not f.lower().endswith(_EXTS):
                continue
            try:
                with Image.open(os.path.join(ref_dir, f)) as im:
                    out.append((f, imagehash.phash(im.convert("RGB"))))
            except Exception:
                pass
    _logo_hashes = out
    return out


def match_logo(image_path: str, ref_dir: str, max_dist: int = 10):
    """Return (ref_name, distance) if the image pHash-matches a reference logo
    within `max_dist` Hamming distance, else None."""
    if not _PHASH_OK:
        return None
    hashes = _logo_hashes if _logo_hashes is not None else _load_logo_hashes(ref_dir)
    if not hashes:
        return None
    try:
        with Image.open(image_path) as im:
            h = imagehash.phash(im.convert("RGB"))
    except Exception:
        return None
    best = min(((name, h - rh) for name, rh in hashes), key=lambda x: x[1], default=None)
    return best if best and best[1] <= max_dist else None


# --------------------------------------------------------------------------- #
#  executive face match (cheap: greyscale histogram + block-diff, no ML)      #
# --------------------------------------------------------------------------- #
def _fingerprint(path: str):
    """A tiny, ML-free face fingerprint: 32x32 greyscale, normalized. Compared by
    correlation. Crude but zero-dependency-heavy and good enough to catch reuse
    of the SAME reference photo. For real face recognition, swap in embeddings."""
    if not (_PHASH_OK and _NP_OK):
        return None
    try:
        with Image.open(path) as im:
            g = im.convert("L").resize((32, 32))
        a = np.asarray(g, dtype="float32").ravel()
        a -= a.mean()
        n = (a * a).sum() ** 0.5
        return a / n if n else None
    except Exception:
        return None


def _load_face_prints(ref_dir: str):
    global _face_prints
    out: list[tuple[str, object]] = []
    if os.path.isdir(ref_dir):
        for f in sorted(os.listdir(ref_dir)):
            if not f.lower().endswith(_EXTS):
                continue
            fp = _fingerprint(os.path.join(ref_dir, f))
            if fp is not None:
                out.append((f, fp))
    _face_prints = out
    return out


def match_face(image_path: str, ref_dir: str, min_score: float = 0.82):
    """Return (ref_name, score) if the image correlates with a reference face
    above `min_score`, else None. Catches reuse of the exact reference photo."""
    if not (_PHASH_OK and _NP_OK):
        return None
    prints = _face_prints if _face_prints is not None else _load_face_prints(ref_dir)
    if not prints:
        return None
    fp = _fingerprint(image_path)
    if fp is None:
        return None
    best = max(((name, float(fp @ rp)) for name, rp in prints),
               key=lambda x: x[1], default=None)
    return best if best and best[1] >= min_score else None


def reload():
    """Force a re-scan of the reference dirs (call after adding reference images)."""
    global _logo_hashes, _face_prints
    _logo_hashes = None
    _face_prints = None
