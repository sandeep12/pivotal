#!/usr/bin/env python3
"""
compare_images.py - pixel-diff a rendered screenshot against a Figma reference.

This is the measuring instrument for the verification loop. It does NOT decide
whether your implementation is "good"; it tells you, objectively, where the
rendered result departs from the Figma export so you know exactly where to look.

It reports:
  - an overall similarity score (% of pixels that match within tolerance),
  - a visual diff image (mismatches painted over a dimmed copy of the reference),
  - the worst regions as bounding boxes, so you can go straight to the problem
    area instead of squinting at the whole screen.

Usage:
    python compare_images.py --reference figma.png --candidate render.png \
        --out-diff diff.png [--tolerance 12] [--grid 32] [--top 8]

The last line of stdout is a JSON blob - parse that if you're driving this
programmatically; everything above it is the human-readable summary.

Deps: Pillow, numpy   ->   pip install pillow numpy
"""
import argparse
import json
import sys

try:
    from PIL import Image
    import numpy as np
except ImportError:
    sys.exit("Missing deps. Run: pip install pillow numpy")


def load_rgb(path):
    return Image.open(path).convert("RGB")


def align(ref, cand):
    """Resize the candidate to the reference size if they differ.

    A size mismatch is itself an important finding (it usually means you
    rendered at the wrong frame dimensions), so we flag it rather than
    silently swallowing it.
    """
    resized = False
    if cand.size != ref.size:
        cand = cand.resize(ref.size, Image.LANCZOS)
        resized = True
    return ref, cand, resized


def main():
    ap = argparse.ArgumentParser(description="Pixel-diff two images for Figma fidelity.")
    ap.add_argument("--reference", required=True, help="Figma reference export (ground truth).")
    ap.add_argument("--candidate", required=True, help="Your rendered screenshot.")
    ap.add_argument("--out-diff", default="diff.png", help="Where to write the diff image.")
    ap.add_argument("--tolerance", type=int, default=12,
                    help="Per-channel difference (0-255) below which a pixel counts as a "
                         "match. Absorbs antialiasing and subpixel font noise so it doesn't "
                         "drown out real mismatches. Default 12.")
    ap.add_argument("--grid", type=int, default=32, help="Hotspot cell size in px. Default 32.")
    ap.add_argument("--top", type=int, default=8, help="How many worst regions to report.")
    args = ap.parse_args()

    ref = load_rgb(args.reference)
    cand = load_rgb(args.candidate)
    ref, cand, resized = align(ref, cand)

    a = np.asarray(ref, dtype=np.int16)
    b = np.asarray(cand, dtype=np.int16)
    chan_diff = np.abs(a - b).max(axis=2)          # H x W, worst channel per pixel
    mismatch = chan_diff > args.tolerance          # bool H x W

    h, w = mismatch.shape
    total = h * w
    mismatched = int(mismatch.sum())
    similarity = 100.0 * (1 - mismatched / total)

    # Diff image: dim the reference to 30% so context is visible, then paint
    # mismatches in red -> yellow by severity (brighter = more wrong).
    base = (np.asarray(ref) * 0.30).astype(np.uint8)
    sev = chan_diff.astype(np.int32)
    base[mismatch, 0] = 255
    base[mismatch, 1] = np.clip(255 - sev[mismatch], 0, 255).astype(np.uint8)
    base[mismatch, 2] = 0
    Image.fromarray(base).save(args.out_diff)

    # Grid hotspots: tile the image and rank cells by how mismatched they are.
    g = max(4, args.grid)
    cells = []
    for gy in range(0, h, g):
        for gx in range(0, w, g):
            cell = mismatch[gy:gy + g, gx:gx + g]
            frac = float(cell.mean()) if cell.size else 0.0
            if frac > 0:
                cells.append((frac, gx, gy, min(g, w - gx), min(g, h - gy)))
    cells.sort(reverse=True)
    hotspots = [
        {"x": x, "y": y, "w": cw, "h": chh, "mismatch_pct": round(frac * 100, 1)}
        for frac, x, y, cw, chh in cells[:args.top]
    ]

    summary = {
        "similarity_pct": round(similarity, 2),
        "mismatched_pixels": mismatched,
        "total_pixels": total,
        "size_mismatch_resized": resized,
        "reference_size": list(ref.size),
        "candidate_size": list(cand.size),
        "tolerance": args.tolerance,
        "diff_image": args.out_diff,
        "hotspots": hotspots,
    }

    print(f"Similarity: {summary['similarity_pct']}%  "
          f"({mismatched:,}/{total:,} px differ, tolerance={args.tolerance})")
    if resized:
        print(f"  ! Size mismatch: candidate {tuple(summary['candidate_size'])} was resized "
              f"to reference {tuple(summary['reference_size'])}. Your frame dimensions are "
              f"probably wrong - fix that before chasing pixel diffs.")
    print(f"  Diff image: {args.out_diff}")
    if hotspots:
        print("  Worst regions (investigate these first):")
        for hs in hotspots:
            print(f"    - ({hs['x']},{hs['y']}) {hs['w']}x{hs['h']}px  ->  {hs['mismatch_pct']}% off")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
