from __future__ import annotations

import glob
import json
import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

try:
    from jproperties import Properties  # type: ignore
except Exception:
    Properties = None  # type: ignore

ITEM_TYPES = ["leather_helmet", "leather_chestplate", "leather_leggings", "leather_boots"]
ARMOR_SLOT = {
    0: "helmet",
    1: "chestplate",
    2: "leggings",
    3: "boots",
}
# Which texture layer each slot uses (1=outer/body, 2=leggings inner)
ARMOR_LAYER_INDEX = {0: 1, 1: 1, 2: 2, 3: 1}


def _log(message: str) -> None:
    print(f"[ARMOR] {message}", flush=True)


def _split_model(model_ref: str) -> Tuple[str, str]:
    if ":" in model_ref:
        namespace, path = model_ref.split(":", 1)
        return namespace, path
    return "minecraft", model_ref


def _write_player_attachable(path: Path, gmdl: str, layer: str, slot_index: int) -> None:
    armor_type = ARMOR_SLOT.get(slot_index, "helmet")
    data = {
        "format_version": "1.10.0",
        "minecraft:attachable": {
            "description": {
                "identifier": f"geyser_custom:{gmdl}.player",
                "item": {f"geyser_custom:{gmdl}": "query.owner_identifier == 'minecraft:player'"},
                "materials": {
                    "default": "armor_leather",
                    "enchanted": "armor_leather_enchanted",
                },
                "textures": {
                    "default": f"textures/armor_layer/{layer}",
                    "enchanted": "textures/misc/enchanted_item_glint",
                },
                "geometry": {"default": f"geometry.player.armor.{armor_type}"},
                "scripts": {"parent_setup": "variable.helmet_layer_visible = 0.0;"},
                "render_controllers": ["controller.render.armor"],
            }
        },
    }
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def _iter_overrides(item_type: str) -> Iterable[Dict[str, object]]:
    # Search all namespaces, not just minecraft
    pattern = f"pack/assets/*/models/item/{item_type}.json"
    overrides: List[Dict[str, object]] = []
    seen_cmds: set = set()

    for item_model_file_str in glob.glob(pattern):
        item_model_file = Path(item_model_file_str)
        try:
            with item_model_file.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception:
            continue

        raw_overrides = data.get("overrides")
        if not isinstance(raw_overrides, list):
            continue

        for entry in raw_overrides:
            if not isinstance(entry, dict):
                continue
            pred = entry.get("predicate", {})
            cmd = pred.get("custom_model_data")
            if cmd is not None and cmd not in seen_cmds:
                seen_cmds.add(cmd)
                overrides.append(entry)

    return overrides


# FIX: recursive glob for attachable lookup
def _find_attachable(namespace: str, model_path: str) -> Optional[Path]:
    base_name = Path(model_path).name
    suffix = f"{base_name}."
    patterns = [
        f"staging/target/rp/attachables/{namespace}/{model_path}*.json",
        f"staging/target/rp/attachables/{namespace}/**/{base_name}.*.json",
        f"staging/target/rp/attachables/**/{base_name}.*.json",
    ]
    seen: set = set()
    for pattern in patterns:
        for candidate_str in glob.glob(pattern, recursive=True):
            if candidate_str in seen:
                continue
            seen.add(candidate_str)
            candidate = Path(candidate_str)
            if suffix in candidate.name:
                return candidate
    return None


def _load_optifine_layer(properties_file: Path, slot_index: int) -> Optional[str]:
    if not properties_file.exists():
        return None

    key = "texture.leather_layer_2" if slot_index == 2 else "texture.leather_layer_1"
    if Properties is not None:
        props = Properties()
        try:
            with properties_file.open("rb") as file:
                props.load(file)
            value = props.get(key)
            if value is None or not getattr(value, "data", ""):
                return None
            return str(value.data).split(".")[0]
        except Exception:
            return None

    try:
        for line in properties_file.read_text(encoding="utf-8-sig").splitlines():
            line = line.split("#", 1)[0].strip()
            if not line or "=" not in line:
                continue
            raw_key, raw_value = line.split("=", 1)
            if raw_key.strip() == key and raw_value.strip():
                return raw_value.strip().split(".")[0]
    except Exception:
        return None
    return None


def _find_armor_texture_fallback(namespace: str, model_path: str, slot_index: int) -> Optional[Path]:
    """
    FIX: Fallback when no OptiFine CIT data exists.
    Try to find armor layer texture directly from model textures or common locations.
    """
    layer_idx = ARMOR_LAYER_INDEX.get(slot_index, 1)
    model_name = Path(model_path).name

    # 1. Read model file and look for layer0/layer1/layer2 texture refs
    for ns in (namespace, "minecraft"):
        model_file = Path(f"pack/assets/{ns}/models/{model_path}.json")
        if model_file.exists():
            try:
                with model_file.open("r", encoding="utf-8") as f:
                    model_data = json.load(f)
                textures = model_data.get("textures", {})
                # Try layer1 first (outer layer), then layer2 (leggings)
                for tex_key in (f"layer{layer_idx}", "layer1", "layer2", "layer0"):
                    tex_ref = textures.get(tex_key)
                    if not isinstance(tex_ref, str):
                        continue
                    if ":" in tex_ref:
                        tex_ns, tex_rel = tex_ref.split(":", 1)
                    else:
                        tex_ns, tex_rel = ns, tex_ref
                    for ext in (".png", ".tga"):
                        source = Path(f"pack/assets/{tex_ns}/textures/{tex_rel}{ext}")
                        if source.exists():
                            return source
            except Exception:
                pass

    # 2. Search models/armor/, textures/models/armor/, textures/armor/
    search_dirs = [
        f"pack/assets/{namespace}/textures/models/armor",
        f"pack/assets/{namespace}/textures/armor",
        f"pack/assets/minecraft/textures/models/armor",
    ]
    for search_dir in search_dirs:
        for ext in (".png", ".tga"):
            for candidate in [
                Path(f"{search_dir}/{model_name}_layer_{layer_idx}{ext}"),
                Path(f"{search_dir}/{model_name}{ext}"),
                Path(f"{search_dir}/{model_name}_layer{layer_idx}{ext}"),
            ]:
                if candidate.exists():
                    return candidate

    # 3. Glob search
    for ext in (".png", ".tga"):
        for candidate in glob.glob(f"pack/assets/{namespace}/textures/**/{model_name}*{ext}", recursive=True):
            return Path(candidate)

    return None


def _copy_model_texture(namespace: str, model_path: str) -> None:
    model_file = Path(f"pack/assets/{namespace}/models/{model_path}.json")
    if not model_file.exists():
        return

    try:
        with model_file.open("r", encoding="utf-8") as file:
            model_data = json.load(file)
        texture_ref = model_data.get("textures", {}).get("layer1")
        if not isinstance(texture_ref, str):
            return
    except Exception:
        return

    if ":" in texture_ref:
        tex_namespace, tex_path = texture_ref.split(":", 1)
    else:
        tex_namespace, tex_path = namespace, texture_ref

    for ext in (".png", ".tga"):
        source = Path(f"pack/assets/{tex_namespace}/textures/{tex_path}{ext}")
        if source.exists():
            destination = Path(f"staging/target/rp/textures/{namespace}/{model_path}.png")
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                shutil.copyfile(source, destination)
            return


def run() -> None:
    converted = 0
    armor_root = Path("pack/assets/minecraft/optifine/cit/ia_generated_armors")
    target_layer_dir = Path("staging/target/rp/textures/armor_layer")
    target_layer_dir.mkdir(parents=True, exist_ok=True)

    for slot_index, item_type in enumerate(ITEM_TYPES):
        for override in _iter_overrides(item_type):
            predicate = override.get("predicate")
            model_ref = override.get("model")

            if not isinstance(predicate, dict) or "custom_model_data" not in predicate:
                continue
            if not isinstance(model_ref, str) or not model_ref.strip():
                continue

            namespace, model_path = _split_model(model_ref)
            model_name = model_path.split("/")[-1]
            if model_name in ITEM_TYPES:
                continue

            # Try OptiFine CIT first
            properties_name = f"{namespace}_{model_name}.properties"
            layer = _load_optifine_layer(armor_root / properties_name, slot_index)

            if layer:
                # OptiFine CIT path
                layer_texture = armor_root / f"{layer}.png"
                if layer_texture.exists():
                    destination_layer = target_layer_dir / f"{layer}.png"
                    if not destination_layer.exists():
                        shutil.copyfile(layer_texture, destination_layer)
            else:
                # FIX: Fallback - find armor texture directly from model
                layer = model_name
                fallback_tex = _find_armor_texture_fallback(namespace, model_path, slot_index)
                if fallback_tex:
                    destination_layer = target_layer_dir / f"{layer}.png"
                    if not destination_layer.exists():
                        shutil.copyfile(fallback_tex, destination_layer)
                    _log(f"Used fallback texture for {model_name}: {fallback_tex}")
                else:
                    _log(f"No armor texture found for {model_name}, skipping")
                    continue

            _copy_model_texture(namespace, model_path)
            attachable_path = _find_attachable(namespace, model_path)
            if not attachable_path:
                _log(f"No attachable found for {namespace}:{model_path}")
                continue

            try:
                with attachable_path.open("r", encoding="utf-8") as file:
                    attachable_data = json.load(file)
                identifier = attachable_data["minecraft:attachable"]["description"]["identifier"]
                gmdl = identifier.split(":", 1)[1]
            except Exception as exc:
                _log(f"Failed to read attachable {attachable_path}: {exc}")
                continue

            player_attachable = attachable_path.with_suffix(".player.json")
            _write_player_attachable(player_attachable, gmdl, layer, slot_index)
            converted += 1

    _log(f"Generated {converted} armor player attachables")


if __name__ == "__main__":
    run()
