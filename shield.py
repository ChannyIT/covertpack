from __future__ import annotations

import glob
import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _log(message: str) -> None:
    print(f"[SHIELD] {message}", flush=True)


# FIX: recursive glob + multiple fallback patterns
def _find_attachable(namespace: str, path: str) -> Optional[str]:
    base_name = Path(path).name
    suffix = f"{base_name}."
    patterns = [
        f"staging/target/rp/attachables/{namespace}/{path}*.json",
        f"staging/target/rp/attachables/{namespace}/**/{base_name}.*.json",
        f"staging/target/rp/attachables/**/{base_name}.*.json",
    ]
    seen: set = set()
    for pattern in patterns:
        for candidate in glob.glob(pattern, recursive=True):
            if candidate in seen:
                continue
            seen.add(candidate)
            if suffix in Path(candidate).name:
                return candidate
    return None


def _archive_superseded_attachable(path: str) -> None:
    source = Path(path)
    if not source.exists():
        return
    archive_root = Path("staging/target/reports/superseded_attachables")
    try:
        relative = source.relative_to("staging/target/rp/attachables")
    except Exception:
        relative = Path(source.name)
    target = archive_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target))


def _cache_overrides() -> None:
    shield_model = Path("pack/assets/minecraft/models/item/shield.json")
    if not shield_model.exists():
        return

    try:
        with shield_model.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception:
        return

    overrides = data.get("overrides")
    if not isinstance(overrides, list):
        return

    for override in overrides:
        if not isinstance(override, dict):
            continue

        model = override.get("model")
        predicate = override.get("predicate")
        if not isinstance(model, str) or model == "item/shield":
            continue
        if not isinstance(predicate, dict) or "custom_model_data" not in predicate:
            continue

        cache_path = Path(f"cache/shield/{predicate['custom_model_data']}.json")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if not cache_path.exists():
            cache_path.write_text("{}", encoding="utf-8")

        try:
            with cache_path.open("r", encoding="utf-8") as file:
                cache_data = json.load(file)
        except Exception:
            cache_data = {}

        if "blocking" in predicate:
            cache_data["blocking"] = model
        else:
            cache_data["default"] = model
        cache_data["check"] = int(cache_data.get("check", 0)) + 1

        with cache_path.open("w", encoding="utf-8") as file:
            json.dump(cache_data, file, indent=2)


def run() -> None:
    _cache_overrides()
    processed = 0

    for cache_file in glob.glob("cache/shield/*.json"):
        try:
            with open(cache_file, "r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception:
            continue

        if data.get("check") != 2:
            continue
        if not isinstance(data.get("default"), str) or not isinstance(data.get("blocking"), str):
            continue

        animation: Dict[str, str] = {}
        animate: List[Dict[str, str]] = []
        safe_attachable = None
        attachable_data = None

        for state in ["default", "blocking"]:
            model_ref = data[state]
            if ":" in model_ref:
                namespace, path = model_ref.split(":", 1)
            else:
                namespace, path = "minecraft", model_ref

            attachable_file = _find_attachable(namespace, path)
            if not attachable_file:
                _log(f"Could not find attachable for {namespace}:{path}")
                continue

            try:
                with open(attachable_file, "r", encoding="utf-8") as file:
                    current_data = json.load(file)
            except Exception as exc:
                _log(f"Failed to load attachable {attachable_file}: {exc}")
                continue

            try:
                description = current_data["minecraft:attachable"]["description"]
            except (KeyError, TypeError):
                continue

            animation_item = description.get("animations", {})
            gmdl = description.get("identifier", "")

            if state == "default":
                safe_attachable = attachable_file
                attachable_data = current_data
                animation["mainhand.first_person"] = animation_item.get("firstperson_main_hand", "")
                animation["mainhand.thierd_person"] = animation_item.get("thirdperson_main_hand", "")
                animation["offhand.first_person"] = animation_item.get("firstperson_off_hand", "")
                animation["offhand.thierd_person"] = animation_item.get("thirdperson_off_hand", "")
                animate = [
                    {"mainhand.thierd_person.block": f"!c.is_first_person && c.item_slot == 'main_hand' && q.is_item_name_any('slot.weapon.mainhand', '{gmdl}') && query.is_sneaking"},
                    {"mainhand.first_person.block": f"c.is_first_person && c.item_slot == 'main_hand' && q.is_item_name_any('slot.weapon.mainhand', '{gmdl}') && query.is_sneaking"},
                    {"mainhand.first_person": f"c.is_first_person && c.item_slot == 'main_hand' && q.is_item_name_any('slot.weapon.mainhand', '{gmdl}') && !query.is_sneaking"},
                    {"mainhand.thierd_person": f"!c.is_first_person && c.item_slot == 'main_hand' && q.is_item_name_any('slot.weapon.mainhand', '{gmdl}') && !query.is_sneaking"},
                    {"offhand.thierd_person.block": f"!c.is_first_person && c.item_slot == 'off_hand' && q.is_item_name_any('slot.weapon.offhand', '{gmdl}') && query.is_sneaking"},
                    {"offhand.first_person.block": f"c.is_first_person && c.item_slot == 'off_hand' && q.is_item_name_any('slot.weapon.offhand', '{gmdl}') && query.is_sneaking"},
                    {"offhand.first_person": f"c.is_first_person && c.item_slot == 'off_hand' && q.is_item_name_any('slot.weapon.offhand', '{gmdl}') && !query.is_sneaking"},
                    {"offhand.thierd_person": f"!c.is_first_person && c.item_slot == 'off_hand' && q.is_item_name_any('slot.weapon.offhand', '{gmdl}') && !query.is_sneaking"},
                ]
            else:
                # blocking state: add blocking animations
                animation["mainhand.thierd_person.block"] = animation_item.get("thirdperson_main_hand", "")
                animation["mainhand.first_person.block"] = animation_item.get("firstperson_main_hand", "")
                animation["offhand.thierd_person.block"] = animation_item.get("thirdperson_off_hand", "")
                animation["offhand.first_person.block"] = animation_item.get("firstperson_off_hand", "")
                # Archive the superseded blocking attachable
                if attachable_file and attachable_file != safe_attachable:
                    _archive_superseded_attachable(attachable_file)

        if safe_attachable and attachable_data and animation and animate:
            try:
                description = attachable_data["minecraft:attachable"]["description"]
                description["animations"] = animation
                description["scripts"] = {
                    "animate": animate,
                    "pre_animation": [
                        "v.main_hand = c.item_slot == 'main_hand';",
                        "v.off_hand = c.item_slot == 'off_hand';",
                    ],
                }
                with open(safe_attachable, "w", encoding="utf-8") as file:
                    json.dump(attachable_data, file, indent=2)
                processed += 1
            except Exception as exc:
                _log(f"Failed to write shield attachable {safe_attachable}: {exc}")

    _log(f"Processed {processed} custom shields")


if __name__ == "__main__":
    run()
