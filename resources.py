from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

PACK_DIR = Path("pack")
TARGET_RP_DIR = Path("staging/target/rp")
OUTPUT_FILE = Path("staging/resource_map.json")
AUDIO_EXTENSIONS = {".ogg", ".wav", ".mp3", ".flac"}
TEXTURE_EXTENSIONS = {".png", ".tga", ".jpg", ".jpeg"}
_TEXTURE_INDEX: Optional[Dict[Tuple[str, str], Path]] = None
_TEXTURE_BASENAME_INDEX: Optional[Dict[Tuple[str, str], List[Path]]] = None


def _log(message: str) -> None:
    print(f"[RESOURCES] {message}", flush=True)


def _safe_load_json(path: Path) -> Optional[Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as file:
            return json.load(file)
    except Exception:
        return None


def _split_ns(reference: str, default_ns: str = "minecraft") -> Tuple[str, str]:
    ref = reference.strip().replace("\\", "/").lstrip("/")
    if ":" in ref:
        ns, rel = ref.split(":", 1)
        return ns or default_ns, rel.strip("/")
    return default_ns, ref.strip("/")


def _normalize_texture_ref(reference: str, default_ns: str = "minecraft") -> Optional[Tuple[str, str]]:
    ref = reference.strip().strip("'\"")
    if not ref or ref.startswith(("#", "http://", "https://")):
        return None
    ns, rel = _split_ns(ref, default_ns)
    if rel.startswith("textures/"):
        rel = rel[len("textures/") :]
    for ext in TEXTURE_EXTENSIONS:
        if rel.lower().endswith(ext):
            rel = rel[: -len(ext)]
            break
    rel = re.sub(r"/+", "/", rel).strip("/")
    if not rel:
        return None
    return ns, rel


def _target_texture_path(namespace: str, rel: str, ext: str) -> Path:
    parts = rel.split("/")
    folder = parts[0] if parts else ""
    subpath = "/".join(parts[1:]) if len(parts) > 1 else parts[0]

    folder_map = {
        "item": "textures/items",
        "items": "textures/items",
        "block": "textures/blocks",
        "blocks": "textures/blocks",
        "entity": "textures/entity",
        "entities": "textures/entity",
        "gui": "textures/gui",
        "font": "font",
        "painting": "textures/painting",
        "paintings": "textures/painting",
        "particle": "textures/particle",
        "particles": "textures/particle",
        "models": "textures/models",
        "armor": "textures/models/armor",
        "environment": "textures/environment",
        "misc": "textures/misc",
        "colormap": "textures/colormap",
        "map": "textures/map",
        "effect": "textures/mob_effect",
        "mob_effect": "textures/mob_effect",
    }

    mapped_folder = folder_map.get(folder)
    if mapped_folder:
        suffix = subpath or Path(rel).name
        if namespace != "minecraft":
            suffix = f"{namespace}/{suffix}"
        return TARGET_RP_DIR / mapped_folder / suffix

    if namespace != "minecraft":
        return TARGET_RP_DIR / "textures" / namespace / rel
    return TARGET_RP_DIR / "textures" / rel


def _resolve_texture_file(namespace: str, rel: str) -> Optional[Path]:
    exact, basename_index = _build_texture_index()
    rel_key = rel.replace("\\", "/").strip("/")
    for ext in TEXTURE_EXTENSIONS:
        if rel_key.lower().endswith(ext):
            rel_key = rel_key[: -len(ext)]
            break
    rel_key = rel_key.lower()

    namespaces = [namespace]
    if namespace != "minecraft":
        namespaces.append("minecraft")

    for ns in namespaces:
        found = exact.get((ns, rel_key))
        if found:
            return found

    basename = Path(rel_key).name
    if basename:
        for ns in namespaces:
            matches = basename_index.get((ns, basename), [])
            if len(matches) == 1:
                return matches[0]
    return None


def _resolve_sprite_texture(sprite: str, namespace_hint: str = "minecraft") -> Optional[Path]:
    normalized = sprite.strip().replace("\\", "/").strip("/")
    if not normalized:
        return None
    for ext in TEXTURE_EXTENSIONS:
        if normalized.lower().endswith(ext):
            normalized = normalized[: -len(ext)]
            break

    parts = normalized.split("/")
    if len(parts) < 2:
        return None

    prefix = "/".join(parts[:2])
    rel_parts = parts[2:]
    folder_by_prefix = {
        "textures/items": "item",
        "textures/blocks": "block",
        "textures/entity": "entity",
        "textures/gui": "gui",
        "textures/particle": "particle",
        "textures/painting": "painting",
        "textures/models": "models",
        "textures/environment": "environment",
        "textures/misc": "misc",
        "textures/colormap": "colormap",
        "textures/map": "map",
        "textures/mob_effect": "mob_effect",
    }
    folder = folder_by_prefix.get(prefix)
    if not folder:
        if parts[0] == "textures" and len(parts) > 2:
            namespace = parts[1]
            rel = "/".join(parts[2:])
            return _resolve_texture_file(namespace, rel)
        return None

    candidates: List[Tuple[str, str]] = []
    if rel_parts:
        first = rel_parts[0]
        rest = "/".join(rel_parts[1:])
        if first and rest:
            candidates.append((first, f"{folder}/{rest}"))
        candidates.append((namespace_hint, f"{folder}/{'/'.join(rel_parts)}"))
        candidates.append(("minecraft", f"{folder}/{'/'.join(rel_parts)}"))
    for namespace, rel in candidates:
        found = _resolve_texture_file(namespace, rel)
        if found:
            return found
    return None


def _copy_file(source: Path, destination: Path) -> bool:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size == source.stat().st_size:
        return False
    shutil.copyfile(source, destination)

    meta = source.with_suffix(source.suffix + ".mcmeta")
    if meta.exists() and meta.is_file():
        shutil.copyfile(meta, destination.with_suffix(destination.suffix + ".mcmeta"))
    return True


def _copy_from_indexed_source(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size == source.stat().st_size:
        return
    shutil.copyfile(source, destination)
    meta = source.with_suffix(source.suffix + ".mcmeta")
    if meta.exists() and meta.is_file():
        shutil.copyfile(meta, destination.with_suffix(destination.suffix + ".mcmeta"))


def _texture_refs_from_json(node: Any, refs: Set[Tuple[str, str]], default_ns: str) -> None:
    if isinstance(node, dict):
        for raw_key, value in node.items():
            key = str(raw_key).strip().lower()
            if isinstance(value, str) and (
                key in {"texture", "textures", "icon", "sprite", "file", "path", "layer0", "layer1", "particle"}
                or key.startswith("layer")
                or "texture" in key
                or "icon" in key
            ):
                parsed = _normalize_texture_ref(value, default_ns)
                if parsed:
                    refs.add(parsed)
            _texture_refs_from_json(value, refs, default_ns)
    elif isinstance(node, list):
        for item in node:
            _texture_refs_from_json(item, refs, default_ns)


def _sprite_refs_from_json(node: Any, refs: Set[str]) -> None:
    if isinstance(node, dict):
        for raw_key, value in node.items():
            key = str(raw_key).strip().lower()
            if isinstance(value, str) and (
                key in {"sprite", "icon", "texture", "path", "file", "image", "background"}
                or "sprite" in key
                or "icon" in key
                or "texture" in key
            ):
                normalized = value.strip().strip("'\"").replace("\\", "/").strip("/")
                if normalized.startswith("textures/"):
                    for ext in TEXTURE_EXTENSIONS:
                        if normalized.lower().endswith(ext):
                            normalized = normalized[: -len(ext)]
                            break
                    refs.add(normalized)
            _sprite_refs_from_json(value, refs)
    elif isinstance(node, list):
        for item in node:
            _sprite_refs_from_json(item, refs)


def _namespace_from_asset_path(path: Path) -> str:
    parts = path.as_posix().split("/")
    try:
        assets_index = parts.index("assets")
        return parts[assets_index + 1]
    except Exception:
        return "minecraft"


def _texture_roots() -> List[Path]:
    roots = [PACK_DIR]
    for extra in (
        Path("providedassetholding"),
        Path("defaultassetholding"),
        Path("staging/providedassetholding"),
        Path("staging/defaultassetholding"),
    ):
        if extra.exists():
            roots.append(extra)
    return roots


def _texture_rel_from_path(path: Path) -> Optional[Tuple[str, str]]:
    parts = path.as_posix().split("/")
    try:
        assets_index = parts.index("assets")
        namespace = parts[assets_index + 1]
        if parts[assets_index + 2] != "textures":
            return None
        rel = "/".join(parts[assets_index + 3:])
    except Exception:
        return None

    suffix = Path(rel).suffix.lower()
    if suffix not in TEXTURE_EXTENSIONS:
        return None
    return namespace, rel[: -len(suffix)].lower()


def _build_texture_index() -> Tuple[Dict[Tuple[str, str], Path], Dict[Tuple[str, str], List[Path]]]:
    global _TEXTURE_INDEX, _TEXTURE_BASENAME_INDEX
    if _TEXTURE_INDEX is not None and _TEXTURE_BASENAME_INDEX is not None:
        return _TEXTURE_INDEX, _TEXTURE_BASENAME_INDEX

    exact: Dict[Tuple[str, str], Path] = {}
    basename: Dict[Tuple[str, str], List[Path]] = {}
    for root in _texture_roots():
        for source in root.glob("**/assets/*/textures/**/*"):
            if not source.is_file() or source.suffix.lower() not in TEXTURE_EXTENSIONS:
                continue
            rel = _texture_rel_from_path(source)
            if rel is None:
                continue
            namespace, rel_key = rel
            exact.setdefault((namespace, rel_key), source)
            basename.setdefault((namespace, Path(rel_key).name), []).append(source)

    _TEXTURE_INDEX = exact
    _TEXTURE_BASENAME_INDEX = basename
    return exact, basename


def _source_label(source: Path) -> str:
    for root in _texture_roots():
        try:
            return source.relative_to(root).as_posix()
        except Exception:
            continue
    return source.as_posix()


def _collect_model_texture_refs() -> Set[Tuple[str, str]]:
    refs: Set[Tuple[str, str]] = set()
    for file_path in list(PACK_DIR.glob("assets/**/models/**/*.json")) + list(PACK_DIR.glob("assets/**/items/**/*.json")):
        data = _safe_load_json(file_path)
        if not isinstance(data, dict):
            continue
        _texture_refs_from_json(data, refs, _namespace_from_asset_path(file_path))
    return refs


def _collect_font_texture_refs() -> Set[Tuple[str, str]]:
    refs: Set[Tuple[str, str]] = set()
    for file_path in PACK_DIR.glob("assets/**/font/**/*.json"):
        data = _safe_load_json(file_path)
        if isinstance(data, dict):
            _texture_refs_from_json(data, refs, _namespace_from_asset_path(file_path))
    return refs


def _collect_sg_texture_refs() -> Set[Tuple[str, str]]:
    refs: Set[Tuple[str, str]] = set()
    manifest = Path("staging/resolved_sprites.json")
    if not manifest.exists():
        return refs
    data = _safe_load_json(manifest)
    if not isinstance(data, dict):
        return refs
    for entry in data.get("sprites", []):
        if not isinstance(entry, dict):
            continue
        sprite = entry.get("sprite")
        namespace = entry.get("namespace")
        if not isinstance(sprite, str) or not isinstance(namespace, str) or not namespace:
            continue

        normalized = sprite.strip().replace("\\", "/").strip("/")
        if normalized.startswith("textures/items/"):
            rel = normalized[len("textures/items/") :]
            ns_prefix = f"{namespace}/"
            if rel.startswith(ns_prefix):
                rel = rel[len(ns_prefix):]
            refs.add((namespace, "item/" + rel))
        elif normalized.startswith("textures/blocks/"):
            rel = normalized[len("textures/blocks/") :]
            ns_prefix = f"{namespace}/"
            if rel.startswith(ns_prefix):
                rel = rel[len(ns_prefix):]
            refs.add((namespace, "block/" + rel))
        elif normalized.startswith("textures/entity/"):
            rel = normalized[len("textures/entity/") :]
            ns_prefix = f"{namespace}/"
            if rel.startswith(ns_prefix):
                rel = rel[len(ns_prefix):]
            refs.add((namespace, "entity/" + rel))
        elif normalized.startswith("textures/gui/"):
            rel = normalized[len("textures/gui/") :]
            ns_prefix = f"{namespace}/"
            if rel.startswith(ns_prefix):
                rel = rel[len(ns_prefix):]
            refs.add((namespace, "gui/" + rel))
        elif normalized.startswith("textures/particle/"):
            rel = normalized[len("textures/particle/") :]
            ns_prefix = f"{namespace}/"
            if rel.startswith(ns_prefix):
                rel = rel[len(ns_prefix):]
            refs.add((namespace, "particle/" + rel))
        elif normalized.startswith("textures/painting/"):
            rel = normalized[len("textures/painting/") :]
            ns_prefix = f"{namespace}/"
            if rel.startswith(ns_prefix):
                rel = rel[len(ns_prefix):]
            refs.add((namespace, "painting/" + rel))
    return refs


def _collect_sprite_texture_refs() -> Set[str]:
    refs: Set[str] = set()
    for manifest in (
        Path("staging/resolved_sprites.json"),
        Path("staging/script.json"),
        Path("staging/sprites.json"),
        Path("staging/geyser_mappings_v2.json"),
        Path("staging/target/geyser_mappings.json"),
    ):
        if not manifest.exists():
            continue
        data = _safe_load_json(manifest)
        _sprite_refs_from_json(data, refs)
    return refs


def _atlas_key_from_output(output: Path) -> Optional[Tuple[str, str]]:
    try:
        rel = output.relative_to(TARGET_RP_DIR).as_posix()
    except Exception:
        return None
    stem = rel.rsplit(".", 1)[0]
    if stem.startswith("textures/items/"):
        key = re.sub(r"[^a-z0-9_.-]+", "_", stem[len("textures/items/") :].lower()).strip("_")
        return "item", key
    if stem.startswith("textures/blocks/"):
        key = re.sub(r"[^a-z0-9_.-]+", "_", stem[len("textures/blocks/") :].lower()).strip("_")
        return "terrain", key
    return None


def _merge_texture_atlases(copied: List[Dict[str, str]]) -> Dict[str, int]:
    atlas_counts = {"item_texture_entries": 0, "terrain_texture_entries": 0}
    item_texture = TARGET_RP_DIR / "textures/item_texture.json"
    terrain_texture = TARGET_RP_DIR / "textures/terrain_texture.json"
    atlas_payloads: Dict[str, Dict[str, Any]] = {}

    for atlas_name, atlas_path, texture_name in (
        ("item", item_texture, "atlas.items"),
        ("terrain", terrain_texture, "atlas.terrain"),
    ):
        data = _safe_load_json(atlas_path)
        if not isinstance(data, dict):
            data = {
                "resource_pack_name": "geyser_custom",
                "texture_name": texture_name,
                "texture_data": {},
            }
        data.setdefault("resource_pack_name", "geyser_custom")
        data.setdefault("texture_name", texture_name)
        data.setdefault("texture_data", {})
        atlas_payloads[atlas_name] = data

    for entry in copied:
        output = entry.get("output")
        if not isinstance(output, str):
            continue
        atlas = _atlas_key_from_output(TARGET_RP_DIR / output)
        if atlas is None:
            continue
        atlas_name, key = atlas
        if not key:
            continue
        texture_stem = output.rsplit(".", 1)[0]
        texture_stem = texture_stem.replace("\\", "/").strip("/")
        texture_data = atlas_payloads[atlas_name].setdefault("texture_data", {})
        if key not in texture_data:
            texture_data[key] = {"textures": texture_stem}
            atlas_counts[f"{atlas_name}_texture_entries"] += 1

    for atlas_name, atlas_path, _ in (
        ("item", item_texture, "atlas.items"),
        ("terrain", terrain_texture, "atlas.terrain"),
    ):
        atlas_path.parent.mkdir(parents=True, exist_ok=True)
        with atlas_path.open("w", encoding="utf-8") as file:
            json.dump(atlas_payloads[atlas_name], file, indent=2, ensure_ascii=False)

    return atlas_counts


def _copy_referenced_textures() -> Dict[str, Any]:
    refs = _collect_model_texture_refs()
    refs.update(_collect_font_texture_refs())
    refs.update(_collect_sg_texture_refs())
    sprite_refs = _collect_sprite_texture_refs()

    copied: List[Dict[str, str]] = []
    missing: List[str] = []
    seen_destinations: Set[str] = set()

    for namespace, rel in sorted(refs):
        source = _resolve_texture_file(namespace, rel)
        if not source:
            missing.append(f"{namespace}:{rel}")
            continue
        destination = _target_texture_path(namespace, rel, source.suffix.lower())
        destination = destination.with_suffix(source.suffix.lower())
        key = destination.as_posix().lower()
        if key in seen_destinations and destination.exists():
            continue
        _copy_from_indexed_source(source, destination)
        seen_destinations.add(key)
        copied.append(
            {
                "source": _source_label(source),
                "output": destination.relative_to(TARGET_RP_DIR).as_posix(),
                "reference": f"{namespace}:{rel}",
            }
        )

    for sprite in sorted(sprite_refs):
        source = _resolve_sprite_texture(sprite)
        if not source:
            missing.append(f"sprite:{sprite}")
            continue
        destination = TARGET_RP_DIR / f"{sprite}{source.suffix.lower()}"
        key = destination.as_posix().lower()
        if key in seen_destinations and destination.exists():
            continue
        _copy_from_indexed_source(source, destination)
        seen_destinations.add(key)
        copied.append(
            {
                "source": _source_label(source),
                "output": destination.relative_to(TARGET_RP_DIR).as_posix(),
                "reference": f"sprite:{sprite}",
            }
        )

    atlas_report = _merge_texture_atlases(copied)

    return {
        "referenced_texture_count": len(refs),
        "referenced_sprite_count": len(sprite_refs),
        "copied_texture_count": len(copied),
        "missing_texture_ref_count": len(missing),
        **atlas_report,
        "textures": copied,
        "missing_texture_refs": missing[:250],
    }


def _iter_pack_files(patterns: Iterable[str]) -> Iterable[Path]:
    seen: Set[Path] = set()
    for pattern in patterns:
        for path in PACK_DIR.glob(pattern):
            if path.is_file() and path not in seen:
                seen.add(path)
                yield path


def _copy_misc_resources() -> Dict[str, Any]:
    copied: List[Dict[str, str]] = []
    patterns = [
        "assets/**/lang/*.json",
        "assets/**/lang/**/*.json",
        "assets/**/texts/*.json",
        "assets/**/texts/**/*.json",
        "assets/**/atlases/*.json",
        "assets/**/atlases/**/*.json",
        "assets/**/color.properties",
        "assets/**/optifine/**/*.properties",
    ]

    for source in _iter_pack_files(patterns):
        try:
            rel = source.relative_to(PACK_DIR)
        except Exception:
            continue
        destination = TARGET_RP_DIR / "imported_java" / rel
        _copy_file(source, destination)
        copied.append({"source": rel.as_posix(), "output": destination.relative_to(TARGET_RP_DIR).as_posix()})

    return {"copied_misc_count": len(copied), "misc_files": copied[:500]}


def run() -> None:
    TARGET_RP_DIR.mkdir(parents=True, exist_ok=True)
    texture_report = _copy_referenced_textures()
    misc_report = _copy_misc_resources()

    payload = {
        **texture_report,
        **misc_report,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)

    _log(
        "Copied "
        f"{payload['copied_texture_count']} referenced textures and "
        f"{payload['copied_misc_count']} metadata files"
    )


if __name__ == "__main__":
    run()
