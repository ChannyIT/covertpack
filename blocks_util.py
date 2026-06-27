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
"""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path
from typing import Optional, Tuple


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
