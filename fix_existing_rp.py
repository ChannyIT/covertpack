#!/usr/bin/env python3
"""
fix_existing_rp.py — Hot-patch an already-converted Bedrock RP folder.

Run this against a previously generated RP directory (the folder that
contains manifest.json, textures/, font/, etc.) to apply all three
bug fixes WITHOUT re-running the full conversion pipeline:

    python3 fix_existing_rp.py  <path-to-rp-folder>

Fixes applied
─────────────
  1. Remove ui/hud_screen.json  (was hiding hunger bar / armor bar / hotbar)
  2. Remove font/default.json   (was using wrong format → broke all font rendering)
  3. Shorten file paths >= 80 chars + patch JSON refs (GeyserMC WARN spam)
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path
from typing import Dict


# ── helpers ──────────────────────────────────────────────────────────────────

def _log(msg: str) -> None:
    print(f"[fix_rp] {msg}", flush=True)


TEXTURE_EXTS = {".png", ".tga", ".jpg", ".jpeg"}
PATCH_EXTS   = {".json", ".lang", ".material", ".mcmeta"}


# ── Fix 1: HUD screen ────────────────────────────────────────────────────────

def fix_hud_screen(rp: Path) -> int:
    """Delete ui/hud_screen.json if it exists.

    Rationale: Writing ANY custom hud_screen.json without re-declaring every
    vanilla control (hunger, armor, health, hotbar, XP…) causes those controls
    to become invisible.  Deleting the file restores Bedrock's built-in HUD
    while still allowing our texture replacements under textures/gui/ to apply.
    """
    hud = rp / "ui" / "hud_screen.json"
    if not hud.exists():
        _log("HUD fix: ui/hud_screen.json not present — nothing to do")
        return 0

    hud.unlink()
    _log("HUD fix: removed ui/hud_screen.json ✓  (hunger/armor/hotbar now visible)")

    ui_dir = rp / "ui"
    try:
        if ui_dir.is_dir() and not any(ui_dir.iterdir()):
            ui_dir.rmdir()
            _log("HUD fix: removed empty ui/ directory")
    except OSError:
        pass
    return 1


# ── Fix 2: Font definition ───────────────────────────────────────────────────

def fix_font_definition(rp: Path) -> int:
    """Delete font/default.json if it exists.

    Rationale: The conversion tool wrote an invalid font/default.json that:
      a) Used a non-existent "trueTypeFont" / "type" key (wrong Bedrock schema)
      b) Referenced glyph pages at "textures/font/glyph_XX" (wrong path —
         they actually live at "font/glyph_XX")
    Either problem alone causes the Bedrock engine to fail font loading, which
    manifests as wrong / missing characters everywhere in the UI.

    The glyph_XX.png files and glyph_sizes.bin in the font/ directory are
    auto-discovered by Bedrock WITHOUT a font/default.json.  Removing the
    broken file is the correct fix.
    """
    font_def = rp / "font" / "default.json"
    if not font_def.exists():
        _log("Font fix: font/default.json not present — nothing to do")
        return 0

    font_def.unlink()
    _log("Font fix: removed font/default.json ✓  (glyph PNGs + glyph_sizes.bin auto-loaded)")
    return 1


# ── Fix 3: Long paths ────────────────────────────────────────────────────────

MAX_PATH_LEN = 79   # Bedrock enforces < 80 chars


def _short_dir(dir_parts: list) -> str:
    """Abbreviate directory parts beyond the first two levels."""
    if len(dir_parts) <= 2:
        return "/".join(dir_parts)
    base = "/".join(dir_parts[:2])
    abbrev = "_".join(p[:3].rstrip("_-") for p in dir_parts[2:] if p)
    return f"{base}/{abbrev}" if abbrev else base


def _short_rel(rel: str, used: set) -> str:
    """Derive a path < 80 chars that is unique within `used`."""
    parts    = rel.split("/")
    filename = parts[-1]
    dir_parts = parts[:-1]
    ext  = Path(filename).suffix
    stem = Path(filename).stem

    sdir = _short_dir(dir_parts)
    max_stem = MAX_PATH_LEN - len(sdir) - 1 - len(ext)   # -1 for "/"

    if max_stem < 6:
        new_stem = hashlib.md5(rel.encode()).hexdigest()[:12]
    elif len(stem) > max_stem:
        h4 = hashlib.md5(rel.encode()).hexdigest()[:4]
        new_stem = stem[:max(1, max_stem - 4)] + h4
    else:
        new_stem = stem

    candidate = f"{sdir}/{new_stem}{ext}"

    # Resolve collisions
    if candidate in used:
        h6 = hashlib.md5(rel.encode()).hexdigest()[:6]
        candidate = f"{sdir}/{h6}{ext}"

    return candidate


def fix_long_paths(rp: Path) -> Dict[str, int]:
    """Rename files >= 80 chars and patch JSON references."""
    rename_map: Dict[str, str] = {}
    used_targets: set = set()

    for fpath in sorted(rp.rglob("*")):
        if not fpath.is_file():
            continue
        try:
            rel = fpath.relative_to(rp).as_posix()
        except ValueError:
            continue
        if len(rel) < 80:
            continue

        new_rel = _short_rel(rel, used_targets)
        if new_rel != rel and len(new_rel) < 80:
            rename_map[rel] = new_rel
            used_targets.add(new_rel)

    if not rename_map:
        _log("Path fix: no paths >= 80 chars found — nothing to do")
        return {"renamed": 0, "patched_files": 0}

    _log(f"Path fix: shortening {len(rename_map)} paths…")

    # Move files
    for old_rel, new_rel in rename_map.items():
        old_path = rp / old_rel
        new_path = rp / new_rel
        if not old_path.exists():
            continue
        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_path), str(new_path))

    # Clean empty dirs
    for old_rel in rename_map:
        parent = (rp / old_rel).parent
        for _ in range(6):
            if parent == rp:
                break
            try:
                if parent.is_dir() and not any(parent.iterdir()):
                    parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    # Build lookup tables
    ext_map:   Dict[str, str] = {}
    noext_map: Dict[str, str] = {}
    for old_rel, new_rel in rename_map.items():
        ext_map[old_rel] = new_rel
        for tex_ext in TEXTURE_EXTS:
            if old_rel.lower().endswith(tex_ext):
                noext_map[old_rel[:-len(tex_ext)]] = new_rel[:-len(tex_ext)]
                break

    # Patch JSON / lang / material references
    patched = 0
    for fpath in rp.rglob("*"):
        if not fpath.is_file() or fpath.suffix.lower() not in PATCH_EXTS:
            continue
        try:
            text = fpath.read_text(encoding="utf-8")
        except Exception:
            continue
        original = text
        for old_ref, new_ref in ext_map.items():
            text = text.replace(old_ref, new_ref)
        for old_ref, new_ref in noext_map.items():
            text = text.replace(old_ref, new_ref)
        if text != original:
            fpath.write_text(text, encoding="utf-8")
            patched += 1

    _log(f"Path fix: renamed {len(rename_map)} files, patched {patched} JSON/lang files ✓")
    return {"renamed": len(rename_map), "patched_files": patched}


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 fix_existing_rp.py <path-to-rp-folder>")
        sys.exit(1)

    rp = Path(sys.argv[1]).resolve()
    if not rp.is_dir():
        print(f"Error: '{rp}' is not a directory")
        sys.exit(1)

    manifest = rp / "manifest.json"
    if not manifest.exists():
        print(f"Warning: '{rp}' does not look like a Bedrock RP (no manifest.json)")

    _log(f"Applying fixes to: {rp}")
    _log("=" * 60)

    fix_hud_screen(rp)
    fix_font_definition(rp)
    stats = fix_long_paths(rp)

    _log("=" * 60)
    _log("All fixes applied.")
    _log(f"  HUD screen JSON removed : see above")
    _log(f"  Font definition removed : see above")
    _log(f"  Paths shortened         : {stats['renamed']} files")
    _log(f"  JSON refs patched       : {stats['patched_files']} files")
    _log("")
    _log("Next steps:")
    _log("  1. Re-zip the RP folder and rename to .mcpack")
    _log("  2. For GeyserMC: place the .mcpack in the Geyser packs folder")
    _log("  3. For standalone MCPE: import the .mcpack on device")


if __name__ == "__main__":
    main()
