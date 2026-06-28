"""
blocks_util.py  –  Bedrock block-conversion helpers
Fixed:
  1. create_terrain_texture: crashed with FileNotFoundError when file didn't
     exist yet. Now initialises the atlas on first call safely.
  2. write_terrain_texture: init helper called by blocks.py before first conversion.
  3. get_am_file: improved glob to search flat directories, without 'block/' prefix,
     and in any namespace folder.
  4. regsister_block (typo alias): kept for backwards-compat.
  5. write_geometry_cube: ensure cube.json always has correct Bedrock format.
  6. resolve_block_texture_direct: BUG FIX – directly resolve and copy a block
     model's textures from the Java pack, so block models are still converted
     even when no item-model attachable exists (which is the common case for
     custom-namespace blocks whose item model pipeline was broken by separate bugs).
"""

from __future__ import annotations

import glob
import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _split_model(model: str) -> Tuple[str, str]:
    """Return (namespace, path) from a model ref like 'ns:block/foo'."""
    model = model.strip()
    if ":" in model:
        namespace, path = model.split(":", 1)
        return namespace.strip() or "minecraft", path.strip()
    return "minecraft", model


def _mapping_file(namespace: str, block: str) -> Path:
    safe_ns = namespace.replace(":", "_")
    return Path(f"staging/target/geyser_block_{safe_ns}_{block}_mappings.json")


# ──────────────────────────────────────────────
# Terrain-texture atlas
# ──────────────────────────────────────────────

_TERRAIN_TEXTURE_PATH = Path("staging/target/rp/textures/terrain_texture.json")

_TERRAIN_ATLAS_TEMPLATE = {
    "resource_pack_name": "geyser_custom",
    "texture_name": "atlas.terrain",
    "texture_data": {},
}


def write_terrain_texture() -> None:
    """Create (or leave intact) the terrain_texture atlas so it is always
    readable when create_terrain_texture() is first called."""
    if _TERRAIN_TEXTURE_PATH.exists():
        try:
            data = json.loads(_TERRAIN_TEXTURE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("texture_data"), dict):
                return
        except Exception:
            pass
    _TERRAIN_TEXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _TERRAIN_TEXTURE_PATH.write_text(
        json.dumps(_TERRAIN_ATLAS_TEMPLATE, indent=4), encoding="utf-8"
    )


def create_terrain_texture(gmdl: str, texture_file: str) -> str:
    """Register texture_file under key block_{gmdl} in the terrain atlas."""
    path = _TERRAIN_TEXTURE_PATH
    data: dict = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    if not isinstance(data.get("texture_data"), dict):
        data = dict(_TERRAIN_ATLAS_TEMPLATE)

    texture_key = f"block_{gmdl}"
    data["texture_data"][texture_key] = {"textures": texture_file}

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=4), encoding="utf-8")
    return texture_key


# ──────────────────────────────────────────────
# Animations / geometry writers
# ──────────────────────────────────────────────

def write_animated_cube() -> None:
    data = {
        "format_version": "1.8.0",
        "animations": {
            "animation.geo_cube.thirdperson_main_hand": {
                "loop": True,
                "bones": {
                    "block": {
                        "rotation": [-20, 145, -10],
                        "position": [0, 14, -6],
                        "scale": [0.375, 0.375, 0.375],
                    }
                },
            },
            "animation.geo_cube.thirdperson_off_hand": {
                "loop": True,
                "bones": {
                    "block": {
                        "rotation": [20, 40, 20],
                        "position": [0, 13, -6],
                        "scale": [0.375, 0.375, 0.375],
                    }
                },
            },
            "animation.geo_cube.head": {
                "loop": True,
                "bones": {"block": {"position": [0, 19.9, 0], "scale": 0.625}},
            },
            "animation.geo_cube.firstperson_main_hand": {
                "loop": True,
                "bones": {
                    "block": {
                        "rotation": [140, 45, 15],
                        "position": [-1, 17, 0],
                        "scale": [0.52, 0.52, 0.52],
                    }
                },
            },
            "animation.geo_cube.firstperson_off_hand": {
                "loop": True,
                "bones": {
                    "block": {
                        "rotation": [-5, 45, -5],
                        "position": [-17.5, 17.5, 15],
                        "scale": [0.52, 0.52, 0.52],
                    }
                },
            },
        },
    }
    path = Path("staging/target/rp/animations/cube.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def write_geometry_cube() -> None:
    """Write the standard 1x1x1 cube geometry used for block items."""
    data = {
        "format_version": "1.16.0",
        "minecraft:geometry": [
            {
                "description": {
                    "identifier": "geometry.cube",
                    "texture_width": 16,
                    "texture_height": 16,
                    "visible_bounds_width": 2,
                    "visible_bounds_height": 2.5,
                    "visible_bounds_offset": [0, 0.75, 0],
                },
                "bones": [
                    {
                        "name": "block",
                        "pivot": [0, 8, 0],
                        "cubes": [
                            {
                                "origin": [-8, 0, -8],
                                "size": [16, 16, 16],
                                "uv": {"north": {"uv": [0, 0], "uv_size": [16, 16]},
                                       "south": {"uv": [0, 0], "uv_size": [16, 16]},
                                       "east":  {"uv": [0, 0], "uv_size": [16, 16]},
                                       "west":  {"uv": [0, 0], "uv_size": [16, 16]},
                                       "up":    {"uv": [0, 0], "uv_size": [16, 16]},
                                       "down":  {"uv": [0, 0], "uv_size": [16, 16]}},
                            }
                        ],
                    }
                ],
            }
        ],
    }
    path = Path("staging/target/rp/models/blocks/cube.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ──────────────────────────────────────────────
# Mapping-file helpers
# ──────────────────────────────────────────────

def write_mapping_block(block: str, namespace: str = "minecraft") -> None:
    block_key = f"{namespace}:{block}"
    data = {
        "format_version": 1,
        "blocks": {
            block_key: {
                "name": block,
                "geometry": "geometry.cube",
                "included_in_creative_inventory": False,
                "only_override_states": True,
                "place_air": True,
                "state_overrides": {},
            }
        },
    }
    path = _mapping_file(namespace, block)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def register_block(
    block: str,
    gmdl: str,
    state: str,
    texture: str,
    block_material: str,
    geometry: str,
    namespace: str = "minecraft",
) -> None:
    path = _mapping_file(namespace, block)
    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    block_key = f"{namespace}:{block}"
    data.setdefault("blocks", {}).setdefault(block_key, {}).setdefault("state_overrides", {})
    data["blocks"][block_key]["state_overrides"][state] = {
        "name": f"block_{gmdl}",
        "display_name": f"block_{gmdl}",
        "geometry": geometry,
        "material_instances": {
            "*": {
                "texture": texture,
                "render_method": block_material,
                "face_dimming": True,
                "ambient_occlusion": True,
            }
        },
    }

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# Backwards-compat alias (typo in original, kept intentionally)
def regsister_block(
    block: str,
    gmdl: str,
    state: str,
    texture: str,
    block_material: str,
    geometry: str,
) -> None:
    register_block(block, gmdl, state, texture, block_material, geometry)


# ──────────────────────────────────────────────
# Attachable / geometry lookups
# ──────────────────────────────────────────────

def get_am_file(model: str) -> Optional[str]:
    """Return path to the Bedrock attachable JSON for *model*.

    Searches multiple patterns in priority order, including flat layouts,
    without-subdir paths, and any-namespace fallbacks.
    """
    namespace, path = _split_model(model)
    base_name = Path(path).name

    # Build candidate search patterns (most-specific first).
    patterns = [
        # Exact namespace + full path
        f"staging/target/rp/attachables/{namespace}/{path}.json",
        f"staging/target/rp/attachables/{namespace}/{path}*.json",
        # Recursive search in namespace dir
        f"staging/target/rp/attachables/{namespace}/**/{base_name}.json",
        f"staging/target/rp/attachables/{namespace}/**/{base_name}.*.json",
        # Without the sub-directory component (flat layout)
        f"staging/target/rp/attachables/{namespace}/{base_name}.json",
        f"staging/target/rp/attachables/{namespace}/{base_name}*.json",
        # Fallback: search any namespace
        f"staging/target/rp/attachables/*/{path}.json",
        f"staging/target/rp/attachables/**/{base_name}.json",
        f"staging/target/rp/attachables/**/{base_name}.*.json",
        # Flat root (no namespace dir)
        f"staging/target/rp/attachables/{path}.json",
        f"staging/target/rp/attachables/{base_name}.json",
    ]

    seen: set = set()
    for pattern in patterns:
        for file_path in glob.glob(pattern, recursive=True):
            if file_path in seen:
                continue
            seen.add(file_path)
            file_stem = Path(file_path).stem.split(".")[0]  # strip .attachable etc.
            if file_stem == base_name:
                return file_path
    return None


def get_geometry_block(model: str) -> str:
    namespace, path = _split_model(model)

    patterns = [
        f"staging/target/rp/models/blocks/{namespace}/{path}.json",
        f"staging/target/rp/models/blocks/{namespace}/**/{Path(path).name}.json",
        f"staging/target/rp/models/blocks/{Path(path).name}.json",
    ]

    for pattern in patterns:
        matches = glob.glob(pattern, recursive=True)
        if not matches:
            continue
        geometry_file = matches[0]
        try:
            raw = Path(geometry_file).read_text(encoding="utf-8")
            if not raw.strip():
                os.remove(geometry_file)
                continue
            data = json.loads(raw)
            return data["minecraft:geometry"][0]["description"]["identifier"]
        except Exception:
            continue

    return "geometry.cube"


# ──────────────────────────────────────────────
# Direct block-texture resolution (BUG FIX)
# ──────────────────────────────────────────────

_PACK_DIR = Path("pack")
_TARGET_RP_DIR = Path("staging/target/rp")
_TEXTURE_EXTS = (".png", ".tga", ".jpg", ".jpeg")


def _find_texture_in_pack(namespace: str, rel: str) -> Optional[Path]:
    """Locate a texture file in the Java pack given a namespace-relative path."""
    # Strip leading 'textures/' if present (Java model JSON often omits it)
    rel = rel.lstrip("/").replace("\\", "/")
    if rel.startswith("textures/"):
        rel = rel[len("textures/"):]

    search_order = [namespace, "minecraft"]
    for ns in search_order:
        base = _PACK_DIR / "assets" / ns / "textures" / rel
        # Try with common texture extensions
        candidates = [base] + [base.with_suffix(ext) for ext in _TEXTURE_EXTS]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        # Fuzzy fallback: search recursively by filename
        stem = Path(rel).stem
        for ext in _TEXTURE_EXTS:
            for hit in (_PACK_DIR / "assets" / ns / "textures").rglob(f"{stem}{ext}"):
                if hit.is_file():
                    return hit
    return None


def _copy_texture_to_bedrock(src: Path, namespace: str, rel_under_textures: str) -> Optional[str]:
    """Copy *src* into the Bedrock RP textures tree, return the RP-relative path without extension."""
    clean_rel = rel_under_textures.lstrip("/").replace("\\", "/")
    if clean_rel.startswith("textures/"):
        clean_rel = clean_rel[len("textures/"):]

    dest_dir = _TARGET_RP_DIR / "textures" / "blocks" / namespace / Path(clean_rel).parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if not dest.exists():
        shutil.copyfile(src, dest)
    # Return path without extension (Bedrock terrain_texture format)
    try:
        rel_out = dest.relative_to(_TARGET_RP_DIR).as_posix()
    except ValueError:
        rel_out = str(dest)
    # Strip extension for terrain_texture reference
    for ext in _TEXTURE_EXTS:
        if rel_out.lower().endswith(ext):
            rel_out = rel_out[: -len(ext)]
            break
    return rel_out


def resolve_block_texture_direct(model_ref: str) -> Optional[str]:
    """Resolve a block model's primary texture directly from the Java pack.

    BUG FIX: blocks.py's original pipeline required pre-existing Bedrock
    attachable files (generated by the item-model pipeline) to look up
    texture references and geometry IDs.  When the item-model pipeline
    produced no attachables (which happened for every custom-namespace pack),
    get_am_file() returned None for every block model, so ALL custom-namespace
    block models were silently skipped.

    This function provides a DIRECT fallback:
      1. Locate the Java block model JSON in the Java pack.
      2. Recursively resolve parent model inheritance.
      3. Extract the first valid texture reference from the 'textures' map.
      4. Copy that texture to the Bedrock RP textures/blocks/ tree.
      5. Register the texture key in terrain_texture.json.
      6. Return the terrain_texture key so blocks.py can call register_block().

    The block is always rendered as geometry.cube (a solid unit cube) since
    fully converting arbitrary Java block geometry to Bedrock geometry would
    require a dedicated geometry converter that is out of scope here.
    """
    namespace, path = _split_model(model_ref)
    # Ensure the path starts from block/
    if not path.startswith("block/"):
        path = f"block/{path}"

    # ── 1. Find the Java block model JSON ────────────────────────────────────
    def _find_model_json(ns: str, p: str) -> Optional[Path]:
        candidates = [
            _PACK_DIR / "assets" / ns / "models" / f"{p}.json",
            _PACK_DIR / "assets" / ns / "models" / f"{p.split('/')[-1]}.json",
        ]
        for c in candidates:
            if c.is_file():
                return c
        # Recursive search
        stem = Path(p).stem
        for hit in (_PACK_DIR / "assets" / ns / "models").rglob(f"{stem}.json"):
            if hit.is_file():
                return hit
        return None

    def _load_json_safe(fp: Path) -> Optional[dict]:
        try:
            with fp.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    # ── 2. Walk parent chain to collect textures (max 8 levels) ─────────────
    textures: Dict[str, str] = {}
    visited: Set[str] = set()
    current_ns, current_path = namespace, path

    for _ in range(8):
        key = f"{current_ns}:{current_path}"
        if key in visited:
            break
        visited.add(key)

        model_file = _find_model_json(current_ns, current_path)
        if model_file is None:
            break

        model_data = _load_json_safe(model_file)
        if model_data is None:
            break

        # Collect textures defined at this level (child overrides parent)
        raw_textures = model_data.get("textures", {})
        if isinstance(raw_textures, dict):
            for k, v in raw_textures.items():
                if isinstance(v, str) and v and k not in textures:
                    textures[k] = v

        # Follow parent
        parent = model_data.get("parent")
        if not isinstance(parent, str) or not parent.strip():
            break
        parent = parent.strip().replace("\\", "/")
        if ":" in parent:
            current_ns, current_path = parent.split(":", 1)
        else:
            current_path = parent

    if not textures:
        return None

    # ── 3. Pick the first usable texture reference ──────────────────────────
    # Priority: "all" > "0" > any key that doesn't start with '#'
    raw_tex: Optional[str] = None
    for prefer in ("all", "0", "particle", "down", "top", "side", "north"):
        candidate = textures.get(prefer)
        if candidate and not candidate.startswith("#"):
            raw_tex = candidate
            break
    if raw_tex is None:
        for v in textures.values():
            if isinstance(v, str) and v and not v.startswith("#"):
                raw_tex = v
                break
    if raw_tex is None:
        return None

    # Resolve texture variable chains (e.g. '#all' → 'namespace:block/foo')
    for _ in range(8):
        if not raw_tex.startswith("#"):
            break
        ref_key = raw_tex[1:]
        resolved = textures.get(ref_key)
        if not resolved or resolved == raw_tex:
            break
        raw_tex = resolved

    if raw_tex.startswith("#"):
        return None

    # Normalise namespace prefix
    if ":" in raw_tex:
        tex_ns, tex_rel = raw_tex.split(":", 1)
    else:
        tex_ns, tex_rel = namespace, raw_tex

    # ── 4. Find and copy the texture file ───────────────────────────────────
    src = _find_texture_in_pack(tex_ns, tex_rel)
    if src is None:
        return None

    # Build a safe terrain key from the model ref
    safe_key = f"{namespace}_{Path(path).name}".replace("/", "_").replace(":", "_")

    dest_rel = _copy_texture_to_bedrock(src, namespace, tex_rel)
    if not dest_rel:
        return None

    # ── 5. Register in terrain_texture.json and return key ───────────────────
    key = f"block_{safe_key}"
    create_terrain_texture(key, dest_rel)
    return key
