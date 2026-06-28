#!/usr/bin/env python3
"""
itemdefs_modern.py
───────────────────────────────────────────────────────────────────────────
Bridges Minecraft 1.21.4+ component-based item definitions
(assets/<namespace>/items/*.json, using a recursive "model" tree of
minecraft:select / minecraft:range_dispatch / minecraft:condition /
minecraft:composite nodes) into the SAME intermediate schema that
converter.sh's legacy predicate-override scan produces for config.json.

WHY THIS EXISTS:
converter.sh's own inline jq attempt at supporting this format
(search for "1.21.4+ item definition format") reads a top-level
".components" field, which does not exist in real item-definition
files (those use a "model" field). It also assumes the referenced
model always lives at "models/item/<item-id>.json", which breaks for
any item with more than one custom_model_data variant. Both of these
silently produce zero usable entries for real-world packs, so
converter.sh's full 3D model + texture-atlas pipeline (driven entirely
by config.json) ends up processing nothing.

Rather than re-deriving the recursive model-tree walk a second time in
jq (error prone), this script imports sg.py -- which already parses
this tree correctly, including every minecraft:select / range_dispatch
/ condition variant -- and reshapes its output into config.json's
expected per-entry shape:

  {
    "<geyserID>": {
      "item": "<vanilla_item_id>",
      "bedrock_icon": {"icon": ..., "frame": ...},
      "nbt": {"CustomModelData": .., "Damage": .., "Unbreakable": ..},
      "path": "./assets/<ns>/models/<...>.json",
      "namespace": "<ns>",
      "model_path": "<dir part of the model path>",
      "model_name": "<file part of the model path>",
      "generated": false
    },
    ...
  }

Usage (run from converter.sh's working directory, AFTER the input pack
has been unzip'd there, and after scratch_files/item_texture.json has
been downloaded):

  python itemdefs_modern.py [pack_dir_or_zip] > scratch_files/item_defs_extra.json

If no path is given, defaults to "." (the already-extracted pack root).
Only emits items recognized as real Java item ids (same vanilla allow
list / GEYSER_ALLOW_CUSTOM_JAVA_ITEMS opt-in that sg.py itself uses),
and only emits entries that carry at least one predicate
(CustomModelData / Damage / Unbreakable) -- matching the legacy
override scan, which never handles bare/no-predicate entries either.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import PurePosixPath

# sg.py lives alongside converter.sh / this script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sg  # noqa: E402  (reuse sg.py's already-correct model tree walker)


def _load_item_texture(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _bedrock_icon(item_texture: dict, item: str) -> dict:
    entry = item_texture.get(item)
    if isinstance(entry, dict) and entry:
        return entry
    return {"icon": "camera", "frame": 0}


def main() -> None:
    pack_path = sys.argv[1] if len(sys.argv) > 1 else "."
    item_texture = _load_item_texture(
        os.environ.get("ITEM_TEXTURE_JSON", "scratch_files/item_texture.json")
    )
    allow_custom_registry = sg._allow_custom_java_items()

    out: dict = {}
    geyser_counter = 0

    with sg.PackReader(pack_path) as reader:
        res = sg.ModelResolver(reader)

        for ns in reader.get_namespaces():
            item_files = sorted(reader.items_dir_files(ns))

            for fpath in item_files:
                data = reader.read_json(fpath)
                if not isinstance(data, dict):
                    continue

                path_obj = PurePosixPath(fpath)
                item_id = path_obj.stem
                parts = list(path_obj.parts)
                if "items" in parts:
                    items_index = parts.index("items")
                    id_parts = parts[items_index + 1:]
                    if id_parts:
                        id_parts = list(id_parts)
                        id_parts[-1] = PurePosixPath(id_parts[-1]).stem
                        item_id = "/".join(id_parts)

                model_node = data.get("model")
                if isinstance(model_node, str) and model_node.strip():
                    model_node = {"type": sg._T_MODEL, "model": model_node.strip()}
                if not isinstance(model_node, dict):
                    continue

                key = item_id if ns == "minecraft" else f"{ns}:{item_id}"
                canonical_key = sg._canonical_java_item_key(
                    key, allow_custom_path=allow_custom_registry
                )
                key_is_runtime_java_item = bool(
                    canonical_key
                    and sg._is_known_java_item_key(
                        canonical_key,
                        allow_custom_registry=allow_custom_registry and ns != "minecraft",
                    )
                )
                # BUG FIX: Do NOT skip custom-namespace items.
                #
                # The previous code dropped ALL non-vanilla items (harshlands:*, baubles:*,
                # iceandfire:*, spartanweaponry:*, etc.) because _is_known_java_item_key()
                # only recognises vanilla Minecraft item IDs.  For GeyserMC modded-server
                # packs these custom items are the ONLY items in the pack, so skipping them
                # left config.json empty, which caused converter.sh's convert_model() to
                # never run and therefore generated ZERO Bedrock attachable/geometry files.
                #
                # GeyserMC format_version:2 supports arbitrary Java item IDs as mapping keys
                # (e.g. "harshlands:some_sword": [...]), so including them here is correct.
                # We therefore allow all items through; the effective item key used in
                # config.json is the full namespaced id for custom items.

                # Effective Java item id used in config / geyser mappings
                if key_is_runtime_java_item:
                    java_item_id = (canonical_key or key).split(":")[-1]
                else:
                    # Custom namespace item – use the full namespaced id so GeyserMC
                    # format_version:2 mappings can address it correctly.
                    java_item_id = key  # e.g. "harshlands:baubles/amulet_slot"

                entries: list = []
                sg.walk_tree(model_node, item_id, res, reader, sg._Ctx(), 0, entries, item_ns=ns)

                for e in entries:
                    java_model = e.get("java_model")
                    if not isinstance(java_model, str) or not java_model:
                        continue

                    nbt: dict = {}
                    if e.get("custom_model_data") is not None:
                        nbt["CustomModelData"] = e["custom_model_data"]
                    if e.get("damage_predicate") is not None:
                        nbt["Damage"] = e["damage_predicate"]
                    if e.get("unbreakable") is True:
                        nbt["Unbreakable"] = True
                    if not nbt:
                        # BUG FIX: Do NOT skip predicate-less entries for custom-namespace
                        # items.  Vanilla items share thousands of items so a predicate is
                        # needed to distinguish variants.  Custom mod items (harshlands:*,
                        # baubles:*, etc.) each have a unique Java item ID, so a single
                        # no-predicate mapping is correct and necessary — GeyserMC will
                        # apply that mapping to ALL instances of that Java item ID.
                        if key_is_runtime_java_item:
                            # Vanilla item: skip bare/no-predicate entries for parity with
                            # legacy override scan.
                            continue
                        # Custom namespace item: include even with no predicates.

                    m_ns, m_path = sg.split_ns(java_model)
                    model_parts = m_path.split("/")
                    model_name = model_parts[-1]
                    model_path = "/".join(model_parts[:-1])

                    geyser_counter += 1
                    geyser_id = f"gmdl_ext_{geyser_counter}"

                    out[geyser_id] = {
                        "item": java_item_id,
                        "bedrock_icon": _bedrock_icon(item_texture, java_item_id),
                        "nbt": nbt,
                        "path": "./" + sg.model_file(m_ns, m_path),
                        "namespace": m_ns,
                        "model_path": model_path,
                        "model_name": model_name,
                        "generated": False,
                        "geyserID": geyser_id,
                    }

    json.dump(out, sys.stdout)


if __name__ == "__main__":
    main()
