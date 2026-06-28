from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple

from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent
PACK_DIR = ROOT_DIR / "pack"
STAGING_DIR = ROOT_DIR / "staging"
TARGET_DIR = STAGING_DIR / "target"
TARGET_RP_DIR = TARGET_DIR / "rp"
TARGET_BP_DIR = TARGET_DIR / "bp"
REPORT_FILE = TARGET_DIR / "reports" / "bedrock_post_report.json"

TEXTURE_EXTENSIONS = (".png", ".tga", ".jpg", ".jpeg")
ALLOWED_TEXTURE_SUFFIXES = TEXTURE_EXTENSIONS + (".mcmeta",)
VANILLA_JAVA_ITEMS = {
    "paper",
    "stick",
    "flint",
    "bow",
    "crossbow",
    "shield",
    "trident",
    "fishing_rod",
    "carrot_on_a_stick",
    "warped_fungus_on_a_stick",
    "wooden_sword",
    "stone_sword",
    "iron_sword",
    "golden_sword",
    "diamond_sword",
    "netherite_sword",
    "wooden_pickaxe",
    "stone_pickaxe",
    "iron_pickaxe",
    "golden_pickaxe",
    "diamond_pickaxe",
    "netherite_pickaxe",
    "wooden_axe",
    "stone_axe",
    "iron_axe",
    "golden_axe",
    "diamond_axe",
    "netherite_axe",
    "wooden_shovel",
    "stone_shovel",
    "iron_shovel",
    "golden_shovel",
    "diamond_shovel",
    "netherite_shovel",
    "wooden_hoe",
    "stone_hoe",
    "iron_hoe",
    "golden_hoe",
    "diamond_hoe",
    "netherite_hoe",
    "leather_helmet",
    "leather_chestplate",
    "leather_leggings",
    "leather_boots",
    "chainmail_helmet",
    "chainmail_chestplate",
    "chainmail_leggings",
    "chainmail_boots",
    "iron_helmet",
    "iron_chestplate",
    "iron_leggings",
    "iron_boots",
    "golden_helmet",
    "golden_chestplate",
    "golden_leggings",
    "golden_boots",
    "diamond_helmet",
    "diamond_chestplate",
    "diamond_leggings",
    "diamond_boots",
    "netherite_helmet",
    "netherite_chestplate",
    "netherite_leggings",
    "netherite_boots",
    "turtle_helmet",
    "elytra",
    "mace",
    "apple",
    "golden_apple",
    "carrot",
    "potato",
    "beetroot",
    "bread",
    "potion",
    "splash_potion",
    "lingering_potion",
    "glass_bottle",
    "experience_bottle",
    "bucket",
    "water_bucket",
    "lava_bucket",
    "milk_bucket",
    "snowball",
    "egg",
    "ender_pearl",
    "firework_rocket",
    "firework_star",
    "book",
    "writable_book",
    "written_book",
    "knowledge_book",
    "map",
    "filled_map",
    "compass",
    "clock",
    "name_tag",
    "lead",
    "saddle",
    "minecart",
    "music_disc_13",
    "music_disc_cat",
    "music_disc_blocks",
    "music_disc_chirp",
    "music_disc_creator",
    "music_disc_creator_music_box",
    "music_disc_far",
    "music_disc_mall",
    "music_disc_mellohi",
    "music_disc_stal",
    "music_disc_strad",
    "music_disc_ward",
    "music_disc_11",
    "music_disc_wait",
    "music_disc_otherside",
    "music_disc_relic",
    "music_disc_5",
    "music_disc_pigstep",
    "music_disc_precipice",
    "music_disc_tears",
}
PBR_SUFFIXES = {
    "_n": "normal",
    "_normal": "normal",
    "_normalgl": "normal",
    "_height": "heightmap",
    "_h": "heightmap",
    "_mer": "mer",
    "_metallic": "mer",
    "_metal": "mer",
    "_roughness": "mer",
    "_r": "mer",
    "_m": "mer",
    "_s": "mer",
    "_e": "emissive",
    "_emission": "emissive",
    "_emit": "emissive",
    "_emissive": "emissive",
}
JAVA_TEXTURE_FOLDER_MAP = {
    "item": "textures/items",
    "items": "textures/items",
    "block": "textures/blocks",
    "blocks": "textures/blocks",
    "entity": "textures/entity",
    "entities": "textures/entity",
    "gui": "textures/gui",
    "painting": "textures/painting",
    "paintings": "textures/painting",
    "particle": "textures/particle",
    "particles": "textures/particle",
    "environment": "textures/environment",
    "misc": "textures/misc",
    "colormap": "textures/colormap",
    "map": "textures/map",
    "models": "textures/models",
    "armor": "textures/models/armor",
    "effect": "textures/mob_effect",
    "mob_effect": "textures/mob_effect",
    "font": "font",
}
POTION_COLORS = {
    "water": (56, 120, 199, 255),
    "mundane": (56, 120, 199, 255),
    "thick": (56, 120, 199, 255),
    "awkward": (56, 120, 199, 255),
    "night_vision": (31, 31, 161, 255),
    "invisibility": (127, 131, 146, 255),
    "leaping": (34, 255, 76, 255),
    "fire_resistance": (228, 154, 58, 255),
    "swiftness": (124, 175, 198, 255),
    "slowness": (90, 108, 129, 255),
    "water_breathing": (46, 82, 153, 255),
    "healing": (248, 36, 35, 255),
    "harming": (67, 10, 9, 255),
    "poison": (78, 147, 49, 255),
    "regeneration": (205, 92, 171, 255),
    "strength": (147, 36, 35, 255),
    "weakness": (72, 77, 72, 255),
    "luck": (51, 153, 0, 255),
    "slow_falling": (247, 242, 235, 255),
    "turtle_master": (51, 102, 0, 255),
}
SPAWN_EGG_COLORS = {
    "allay": ((0, 205, 255, 255), (0, 82, 204, 255)),
    "armadillo": ((173, 124, 95, 255), (99, 64, 50, 255)),
    "axolotl": ((250, 208, 220, 255), (121, 47, 71, 255)),
    "bee": ((237, 189, 64, 255), (43, 43, 43, 255)),
    "blaze": ((241, 178, 46, 255), (255, 255, 0, 255)),
    "bogged": ((91, 117, 72, 255), (202, 225, 141, 255)),
    "camel": ((193, 129, 67, 255), (99, 63, 35, 255)),
    "cat": ((239, 184, 131, 255), (67, 44, 31, 255)),
    "cave_spider": ((12, 25, 29, 255), (168, 34, 34, 255)),
    "chicken": ((161, 161, 161, 255), (255, 0, 0, 255)),
    "cod": ((198, 134, 70, 255), (232, 226, 205, 255)),
    "cow": ((68, 51, 35, 255), (255, 255, 255, 255)),
    "creeper": ((13, 159, 0, 255), (0, 0, 0, 255)),
    "dolphin": ((34, 103, 143, 255), (163, 188, 202, 255)),
    "drowned": ((80, 110, 102, 255), (121, 159, 136, 255)),
    "ender_dragon": ((26, 26, 26, 255), (177, 50, 177, 255)),
    "enderman": ((22, 22, 22, 255), (177, 0, 177, 255)),
    "endermite": ((22, 22, 22, 255), (94, 94, 94, 255)),
    "evoker": ((149, 154, 157, 255), (31, 31, 31, 255)),
    "fox": ((210, 88, 28, 255), (235, 235, 235, 255)),
    "frog": ((125, 170, 55, 255), (214, 189, 77, 255)),
    "ghast": ((241, 241, 241, 255), (188, 188, 188, 255)),
    "glow_squid": ((9, 22, 26, 255), (82, 183, 196, 255)),
    "goat": ((164, 157, 145, 255), (78, 71, 63, 255)),
    "guardian": ((94, 119, 94, 255), (255, 128, 128, 255)),
    "hoglin": ((196, 124, 92, 255), (61, 31, 31, 255)),
    "horse": ((198, 113, 55, 255), (62, 31, 0, 255)),
    "husk": ((121, 119, 85, 255), (228, 230, 196, 255)),
    "iron_golem": ((224, 224, 224, 255), (129, 86, 49, 255)),
    "llama": ((199, 187, 152, 255), (77, 64, 41, 255)),
    "magma_cube": ((52, 24, 12, 255), (255, 164, 42, 255)),
    "mooshroom": ((161, 39, 34, 255), (255, 255, 255, 255)),
    "ocelot": ((239, 184, 131, 255), (59, 49, 26, 255)),
    "panda": ((255, 255, 255, 255), (0, 0, 0, 255)),
    "parrot": ((11, 123, 142, 255), (255, 0, 0, 255)),
    "phantom": ((67, 72, 101, 255), (136, 146, 181, 255)),
    "pig": ((240, 160, 160, 255), (219, 117, 117, 255)),
    "piglin": ((244, 183, 143, 255), (83, 44, 43, 255)),
    "piglin_brute": ((89, 58, 31, 255), (244, 183, 143, 255)),
    "pillager": ((83, 90, 89, 255), (149, 154, 157, 255)),
    "polar_bear": ((238, 238, 238, 255), (204, 204, 204, 255)),
    "pufferfish": ((245, 197, 68, 255), (55, 55, 55, 255)),
    "rabbit": ((153, 117, 80, 255), (226, 207, 170, 255)),
    "ravager": ((117, 126, 126, 255), (90, 96, 96, 255)),
    "salmon": ((165, 102, 89, 255), (104, 64, 56, 255)),
    "sheep": ((224, 224, 224, 255), (255, 181, 181, 255)),
    "shulker": ((151, 93, 151, 255), (88, 54, 88, 255)),
    "silverfish": ((106, 106, 106, 255), (48, 48, 48, 255)),
    "skeleton": ((199, 199, 199, 255), (73, 73, 73, 255)),
    "slime": ((81, 128, 65, 255), (127, 204, 25, 255)),
    "sniffer": ((132, 88, 68, 255), (94, 57, 45, 255)),
    "snow_golem": ((238, 238, 238, 255), (249, 128, 29, 255)),
    "spider": ((52, 43, 38, 255), (148, 28, 27, 255)),
    "squid": ((34, 49, 65, 255), (112, 146, 190, 255)),
    "stray": ((98, 116, 116, 255), (215, 239, 239, 255)),
    "strider": ((139, 72, 58, 255), (80, 35, 29, 255)),
    "tadpole": ((56, 43, 24, 255), (112, 87, 52, 255)),
    "trader_llama": ((199, 187, 152, 255), (229, 229, 229, 255)),
    "tropical_fish": ((239, 154, 76, 255), (246, 225, 67, 255)),
    "turtle": ((225, 214, 170, 255), (84, 71, 45, 255)),
    "vex": ((128, 158, 158, 255), (67, 90, 90, 255)),
    "villager": ((86, 51, 28, 255), (196, 129, 77, 255)),
    "vindicator": ((149, 154, 157, 255), (31, 31, 31, 255)),
    "wandering_trader": ((69, 91, 167, 255), (203, 197, 129, 255)),
    "warden": ((12, 35, 39, 255), (27, 79, 85, 255)),
    "witch": ((52, 78, 47, 255), (81, 0, 145, 255)),
    "wither": ((20, 20, 20, 255), (80, 80, 80, 255)),
    "wither_skeleton": ((20, 20, 20, 255), (71, 71, 71, 255)),
    "wolf": ((216, 216, 216, 255), (135, 135, 135, 255)),
    "zoglin": ((196, 124, 92, 255), (83, 71, 65, 255)),
    "zombie": ((0, 151, 75, 255), (121, 102, 76, 255)),
    "zombie_villager": ((0, 151, 75, 255), (86, 51, 28, 255)),
    "zombified_piglin": ((234, 162, 142, 255), (79, 110, 53, 255)),
}
UNSUPPORTED_HINTS = {
    "optifine_shader": ("assets/**/shaders/**/*", "OptiFine shader programs cannot be represented by Bedrock resource packs."),
    "optifine_ctm": ("assets/**/optifine/ctm/**/*", "OptiFine CTM is copied only as source metadata; Bedrock needs block permutations or geometry."),
    "optifine_cem": ("assets/**/optifine/cem/**/*", "OptiFine CEM does not map 1:1 to Bedrock entities without geometry/controller authoring."),
    "optifine_cit": ("assets/**/optifine/cit/**/*", "OptiFine CIT is converted through CustomModelData-style mappings when possible; unsupported predicates are reported."),
    "optifine_anim": ("assets/**/optifine/anim/**/*", "OptiFine custom animations are approximated only when they are texture mcmeta animations."),
    "modelengine_source": ("**/*modelengine*/*", "ModelEngine assets are approximated as Bedrock geometry/controllers when source data is present."),
    "gui_3d_items": ("assets/**/models/item/**/*.json", "Bedrock does not render arbitrary 3D item models inside every GUI slot."),
    "display_entity": ("assets/**/display*/**/*", "DisplayEntity data is approximated only when converted into entity/armor-stand style assets."),
    "display_entity_root": ("**/*display_entity*.*", "DisplayEntity data is approximated only when converted into entity/armor-stand style assets."),
    "java_shaders_core": ("assets/**/shaders/**/*", "Java shader/core shader packs are not portable to Bedrock resource packs."),
    "gui_java_layout": ("assets/**/textures/gui/**/*.png", "Java GUI textures are copied; Bedrock hud_screen.json can only approximate layout and cannot reproduce every Java screen."),
    "labpbr_source": ("assets/**/*_n.png", "LabPBR/PBR sources are converted to Bedrock texture_set JSON when matching color textures exist."),
}


def _log(message: str) -> None:
    print(f"[BEDROCK_POST] {message}", flush=True)


def _load_json(path: Path) -> Optional[Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as file:
            return json.load(file)
    except Exception:
        return None


def _is_json_valid(path: Path) -> bool:
    if _load_json(path) is not None:
        return True
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except Exception:
        return False
    stripped = raw.strip()
    return bool(stripped) and not stripped.startswith(("{", "["))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)
        file.write("\n")


def _iter_files(root: Path, patterns: Iterable[str]) -> Iterator[Path]:
    seen: Set[Path] = set()
    for pattern in patterns:
        try:
            for path in root.glob(pattern):
                if path.is_file() and path not in seen:
                    seen.add(path)
                    yield path
        except OSError:
            continue


def _relative_to_pack(path: Path) -> str:
    try:
        return path.relative_to(PACK_DIR).as_posix()
    except Exception:
        return path.as_posix()


def _strip_texture_ext(value: str) -> str:
    text = value.replace("\\", "/").strip().strip("/")
    for ext in TEXTURE_EXTENSIONS:
        if text.lower().endswith(ext):
            return text[: -len(ext)]
    return text


def _sanitize_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9_.-]+", "_", value.lower()).strip("_") or "asset"


def _allow_custom_java_items() -> bool:
    return os.getenv("GEYSER_ALLOW_CUSTOM_JAVA_ITEMS", "").strip().lower() in {"1", "true", "yes", "on"}


def _java_item_key_parts(item_id: Any, *, allow_custom_path: bool = False) -> Optional[Tuple[str, str]]:
    if not isinstance(item_id, str):
        return None
    raw = item_id.strip().replace("\\", "/").lower()
    if not raw:
        return None
    if ":" in raw:
        namespace, name = raw.split(":", 1)
        namespace = namespace or "minecraft"
    else:
        namespace, name = "minecraft", raw
    namespace = re.sub(r"[^a-z0-9_.-]+", "_", namespace).strip("_.-")
    name = re.sub(r"[^a-z0-9_./-]+", "_", name).strip("_.-/")
    if not namespace or not name:
        return None
    if "/" in name and not (allow_custom_path and namespace != "minecraft"):
        return None
    return namespace, name


def _canonical_java_item_key(item_id: Any, *, allow_custom_path: bool = False) -> Optional[str]:
    parts = _java_item_key_parts(item_id, allow_custom_path=allow_custom_path)
    if not parts:
        return None
    namespace, name = parts
    return f"{namespace}:{name}"


def _mapping_entry_has_predicate(entry: Dict[str, Any]) -> bool:
    # Geyser v2 expresses damage/unbreakable via the "predicate" system, so an
    # entry that carries a "predicate" (or the legacy top-level fields) is a
    # runtime-matched mapping and must be kept.
    if any(entry.get(key) is not None for key in ("custom_model_data", "damage_predicate", "unbreakable")):
        return True
    return entry.get("predicate") is not None


def _known_java_item_key(item_id: Any) -> bool:
    allow_custom_items = _allow_custom_java_items()
    parts = _java_item_key_parts(item_id, allow_custom_path=allow_custom_items)
    if not parts:
        return False
    namespace, name = parts
    if namespace == "minecraft":
        return name in VANILLA_JAVA_ITEMS
    return allow_custom_items


def _split_ns(reference: str, default_ns: str = "minecraft") -> Tuple[str, str]:
    ref = reference.strip().replace("\\", "/").strip("/")
    if ":" in ref:
        namespace, rel = ref.split(":", 1)
        return namespace or default_ns, rel.strip("/")
    return default_ns, ref


def _java_texture_ref_to_output(reference: str, default_ns: str = "minecraft") -> Optional[Path]:
    if not isinstance(reference, str):
        return None
    ref = reference.strip().strip("'\"")
    if not ref or ref.startswith(("#", "http://", "https://")):
        return None
    namespace, rel = _split_ns(_strip_texture_ext(ref), default_ns)
    if rel.startswith("textures/"):
        rel = rel[len("textures/") :]
    rel = re.sub(r"/+", "/", rel).strip("/")
    if not rel:
        return None

    parts = rel.split("/")
    folder = parts[0]
    mapped = JAVA_TEXTURE_FOLDER_MAP.get(folder)
    if mapped:
        suffix = "/".join(parts[1:]) if len(parts) > 1 else parts[0]
        if namespace != "minecraft":
            suffix = f"{namespace}/{suffix}"
        return TARGET_RP_DIR / mapped / suffix

    if namespace != "minecraft":
        return TARGET_RP_DIR / "textures" / namespace / rel
    return TARGET_RP_DIR / "textures" / rel


def _java_texture_path_to_output(source: Path) -> Optional[Path]:
    try:
        parts = source.relative_to(PACK_DIR).parts
    except Exception:
        return None
    try:
        assets_index = parts.index("assets")
        namespace = parts[assets_index + 1]
        if parts[assets_index + 2] != "textures":
            return None
        rel = PurePosixPath(*parts[assets_index + 3 :]).as_posix()
    except Exception:
        return None

    suffix = source.suffix.lower()
    if suffix not in TEXTURE_EXTENSIONS:
        return None
    return _java_texture_ref_to_output(f"{namespace}:{_strip_texture_ext(rel)}", namespace)


def _copy_texture_lossless(source: Path, destination_stem: Path) -> bool:
    suffix = source.suffix.lower()
    if suffix not in TEXTURE_EXTENSIONS:
        return False
    destination = destination_stem.with_suffix(suffix)
    destination.parent.mkdir(parents=True, exist_ok=True)

    copied = False
    try:
        if not destination.exists() or source.stat().st_size != destination.stat().st_size:
            shutil.copyfile(source, destination)
            copied = True
    except OSError:
        return False

    meta = source.with_suffix(source.suffix + ".mcmeta")
    if meta.exists() and meta.is_file():
        try:
            shutil.copyfile(meta, destination.with_suffix(destination.suffix + ".mcmeta"))
        except OSError:
            pass
    return copied


def _colorize_template(template: Image.Image, color: Tuple[int, int, int, int]) -> Image.Image:
    rgba = template.convert("RGBA")
    pixels = rgba.load()
    cr, cg, cb, ca = color
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            shade = max(r, g, b) / 255.0
            pixels[x, y] = (
                int(cr * shade),
                int(cg * shade),
                int(cb * shade),
                int(a * (ca / 255.0)),
            )
    return rgba


def _alpha_composite(base: Image.Image, overlay: Image.Image) -> Image.Image:
    output = base.convert("RGBA")
    output.alpha_composite(overlay.convert("RGBA"))
    return output


def _pack_description() -> str:
    data = _load_json(PACK_DIR / "pack.mcmeta")
    if isinstance(data, dict):
        desc = (data.get("pack") or {}).get("description")
        if isinstance(desc, str) and desc.strip():
            return re.sub(r"[\u00a7Â§][0-9a-fk-orx]", "", desc).strip()
        if isinstance(desc, dict):
            text = desc.get("text") or desc.get("translate")
            if isinstance(text, str) and text.strip():
                return text.strip()
    return "Geyser Java-to-Bedrock Converted Pack"


def _normalize_min_engine_version() -> List[int]:
    raw = os.getenv("MIN_ENGINE_VERSION", "1.21.0").strip()
    parts: List[int] = []
    for token in re.split(r"[.,_\- ]+", raw):
        if token.isdigit():
            parts.append(int(token))
    if len(parts) >= 2:
        return (parts + [0, 0, 0])[:3]
    return [1, 21, 0]


def _ensure_manifest(path: Path, pack_type: str, name_suffix: str, dependency_uuid: Optional[str] = None) -> str:
    data = _load_json(path)
    if not isinstance(data, dict):
        data = {}

    header = data.setdefault("header", {})
    if not isinstance(header, dict):
        header = {}
        data["header"] = header

    modules = data.setdefault("modules", [])
    if not isinstance(modules, list):
        modules = []
        data["modules"] = modules

    fresh_uuids = os.getenv("BEDROCK_POST_FRESH_UUIDS", "true").strip().lower() not in {"0", "false", "no", "off"}
    header_uuid = str(uuid.uuid4() if fresh_uuids else (header.get("uuid") or uuid.uuid4())).lower()
    module_uuid = str(uuid.uuid4()).lower()
    if not fresh_uuids and modules and isinstance(modules[0], dict) and modules[0].get("uuid"):
        module_uuid = str(modules[0].get("uuid")).lower()

    description = _pack_description()
    header.update(
        {
            "name": str(header.get("name") or f"{description} {name_suffix}")[:64],
            "description": str(header.get("description") or description)[:256],
            "uuid": header_uuid,
            "version": header.get("version") if isinstance(header.get("version"), list) else [1, 0, 0],
            "min_engine_version": _normalize_min_engine_version(),
        }
    )

    module_type = "resources" if pack_type == "resources" else "data"
    module = modules[0] if modules and isinstance(modules[0], dict) else {}
    module.update(
        {
            "type": module_type,
            "uuid": module_uuid,
            "version": module.get("version") if isinstance(module.get("version"), list) else [1, 0, 0],
            "description": module.get("description") or header["description"],
        }
    )
    data["format_version"] = 2
    data["modules"] = [module] + [m for m in modules[1:] if isinstance(m, dict)]

    if pack_type == "data" and dependency_uuid:
        dependencies = data.setdefault("dependencies", [])
        if not isinstance(dependencies, list):
            dependencies = []
        dep = {"uuid": dependency_uuid, "version": [1, 0, 0]}
        if not any(isinstance(item, dict) and item.get("uuid") == dependency_uuid for item in dependencies):
            dependencies.append(dep)
        data["dependencies"] = dependencies

    _write_json(path, data)
    return header_uuid


def _ensure_pack_icon(pack_root: Path) -> bool:
    target = pack_root / "pack_icon.png"
    source_candidates = [PACK_DIR / "pack.png", PACK_DIR / "assets" / "icon.png", ROOT_DIR / "blank256.png"]
    source = next((candidate for candidate in source_candidates if candidate.exists()), None)
    if source is None:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(source) as image:
            icon = image.convert("RGBA").resize((256, 256), Image.Resampling.LANCZOS)
            icon.save(target)
        return True
    except Exception:
        shutil.copyfile(source, target)
        return True


def _java_locale_to_bedrock(locale: str) -> str:
    parts = locale.replace("-", "_").split("_")
    if len(parts) >= 2:
        return f"{parts[0].lower()}_{parts[1].upper()}"
    return locale


def _flatten_lang_value(value: Any) -> str:
    if isinstance(value, str):
        return value.replace("\r", "").replace("\n", "\\n")
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        chunks: List[str] = []
        for item in value:
            if isinstance(item, dict):
                chunks.append(str(item.get("text") or item.get("translate") or ""))
            else:
                chunks.append(str(item))
        return "".join(chunks).replace("\r", "").replace("\n", "\\n")
    if isinstance(value, dict):
        return str(value.get("text") or value.get("translate") or "").replace("\r", "").replace("\n", "\\n")
    return ""


def _convert_lang_files() -> Dict[str, Any]:
    texts_dir = TARGET_RP_DIR / "texts"
    texts_dir.mkdir(parents=True, exist_ok=True)
    languages: Set[str] = set()
    converted = 0

    for lang_file in _iter_files(PACK_DIR, ("assets/**/lang/*.json", "assets/**/lang/**/*.json")):
        data = _load_json(lang_file)
        if not isinstance(data, dict):
            continue
        locale = _java_locale_to_bedrock(lang_file.stem)
        output = texts_dir / f"{locale}.lang"
        lines = [f"{key}={_flatten_lang_value(value)}" for key, value in sorted(data.items())]
        if lines:
            existing = output.read_text(encoding="utf-8") if output.exists() else ""
            suffix = ("\n" if existing and not existing.endswith("\n") else "")
            output.write_text(existing + suffix + "\n".join(lines) + "\n", encoding="utf-8")
            languages.add(locale)
            converted += 1

    for existing in texts_dir.glob("*.lang"):
        languages.add(existing.stem)
    if not languages:
        languages.update({"en_US", "en_GB"})
    if "en_US" in languages and "en_GB" not in languages:
        source = texts_dir / "en_US.lang"
        target = texts_dir / "en_GB.lang"
        if source.exists() and not target.exists():
            shutil.copyfile(source, target)
        languages.add("en_GB")

    _write_json(texts_dir / "languages.json", sorted(languages))
    return {"converted_lang_json": converted, "language_count": len(languages)}


def _texture_stem_from_output(path: Path) -> Optional[str]:
    try:
        rel = path.relative_to(TARGET_RP_DIR).as_posix()
    except Exception:
        return None
    if not rel.startswith("textures/"):
        return None
    return rel.rsplit(".", 1)[0]


def _read_animation_meta(meta_path: Path) -> Optional[Dict[str, Any]]:
    data = _load_json(meta_path)
    if not isinstance(data, dict):
        return None
    animation = data.get("animation")
    return animation if isinstance(animation, dict) else None


def _convert_mcmeta_flipbooks() -> Dict[str, Any]:
    flipbook_path = TARGET_RP_DIR / "textures" / "flipbook_textures.json"
    existing = _load_json(flipbook_path)
    entries: List[Dict[str, Any]] = existing if isinstance(existing, list) else []
    seen = {entry.get("flipbook_texture") for entry in entries if isinstance(entry, dict)}
    converted = 0

    for meta_path in TARGET_RP_DIR.glob("textures/**/*.mcmeta"):
        texture_path = Path(str(meta_path)[: -len(".mcmeta")])
        if not texture_path.exists() or texture_path.suffix.lower() not in TEXTURE_EXTENSIONS:
            continue
        stem = _texture_stem_from_output(texture_path)
        if not stem or stem in seen:
            continue
        animation = _read_animation_meta(meta_path)
        if animation is None:
            continue

        try:
            with Image.open(texture_path) as image:
                frame_size = int(animation.get("width") or min(image.width, image.height))
                frame_count = max(1, image.height // max(1, frame_size))
        except Exception:
            frame_size = int(animation.get("width") or 16)
            frame_count = 1

        ticks = max(1, int(animation.get("frametime") or 1))
        # Honour Java's explicit "frames" list (custom order + optional per-frame
        # time). Bedrock has no per-frame duration, so a frame with time T is
        # approximated by repeating its index round(T / ticks_per_frame) times.
        frames_field = animation.get("frames")
        frames_list: List[int] = []
        if isinstance(frames_field, list) and frames_field:
            for fr in frames_field:
                if isinstance(fr, bool):
                    continue
                if isinstance(fr, (int, float)):
                    frames_list.append(int(fr))
                elif isinstance(fr, dict):
                    idx = fr.get("index")
                    if not isinstance(idx, int) or isinstance(idx, bool):
                        continue
                    frame_time = fr.get("time")
                    reps = 1
                    if isinstance(frame_time, (int, float)) and not isinstance(frame_time, bool) and frame_time > 0:
                        reps = max(1, round(float(frame_time) / ticks))
                    frames_list.extend([idx] * reps)
        if not frames_list:
            frames_list = list(range(frame_count))

        entry: Dict[str, Any] = {
            "flipbook_texture": stem,
            "atlas_tile": stem,
            "ticks_per_frame": ticks,
            "frames": frames_list,
        }
        # Java "interpolate" maps to Bedrock "blend_frames"; default is true on
        # Bedrock, so emit it explicitly in both directions to preserve intent.
        entry["blend_frames"] = animation.get("interpolate") is True
        entries.append(entry)
        seen.add(stem)
        converted += 1

    if entries:
        _write_json(flipbook_path, entries)
    return {"flipbook_entry_count": len(entries), "mcmeta_converted": converted}


def _copy_java_texture_tree() -> Dict[str, Any]:
    copied = 0
    skipped = 0
    for source in _iter_files(PACK_DIR, ("assets/**/textures/**/*",)):
        if source.suffix.lower() not in ALLOWED_TEXTURE_SUFFIXES:
            continue
        if source.suffix.lower() == ".mcmeta":
            texture_source = Path(str(source)[: -len(".mcmeta")])
            destination_stem = _java_texture_path_to_output(texture_source)
            if destination_stem is None:
                skipped += 1
                continue
            destination_texture = destination_stem.with_suffix(texture_source.suffix.lower())
            destination = destination_texture.with_suffix(destination_texture.suffix + ".mcmeta")
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copyfile(source, destination)
                copied += 1
            except OSError:
                skipped += 1
            continue

        destination_stem = _java_texture_path_to_output(source)
        if destination_stem is None:
            skipped += 1
            continue
        if _copy_texture_lossless(source, destination_stem):
            copied += 1
    return {"java_texture_tree_copied": copied, "java_texture_tree_skipped": skipped}


def _split_emissive_and_transparency() -> Dict[str, Any]:
    separated = 0
    for texture in TARGET_RP_DIR.glob("textures/**/*"):
        if not texture.is_file() or texture.suffix.lower() not in TEXTURE_EXTENSIONS:
            continue
        stem = texture.with_suffix("")
        lower_name = stem.name.lower()
        if lower_name.endswith(("_e", "_emissive", "_emission", "_emit")):
            continue
        emissive = None
        for suffix in ("_e", "_emissive", "_emission", "_emit"):
            candidate = stem.with_name(stem.name + suffix).with_suffix(texture.suffix.lower())
            if candidate.exists():
                emissive = candidate
                break
        if emissive is None:
            continue
        try:
            with Image.open(texture) as base_image, Image.open(emissive) as emissive_image:
                base_rgba = base_image.convert("RGBA")
                emissive_rgba = emissive_image.convert("RGBA").resize(base_rgba.size, Image.Resampling.NEAREST)
                bp = base_rgba.load()
                ep = emissive_rgba.load()
                for y in range(base_rgba.height):
                    for x in range(base_rgba.width):
                        er, eg, eb, ea = ep[x, y]
                        if ea > 0 and (er or eg or eb):
                            br, bg, bb, ba = bp[x, y]
                            bp[x, y] = (br, bg, bb, max(ba, ea))
                base_rgba.save(texture)
                emissive_rgba.save(emissive)
                separated += 1
        except Exception:
            continue
    return {"emissive_transparency_separated": separated}


def _convert_png_to_tga_for_alpha_masks() -> Dict[str, Any]:
    converted = 0
    candidate_set: Set[Path] = set(TARGET_RP_DIR.glob("textures/models/armor/**/*.png"))
    candidate_set.update(TARGET_RP_DIR.glob("textures/armor_layer/**/*.png"))
    candidate_set.update(TARGET_RP_DIR.glob("textures/entity/equipment/**/*.png"))
    candidate_set.update(TARGET_RP_DIR.glob("textures/models/**/*.png"))
    candidates = sorted(candidate_set)
    for png_path in candidates:
        if not png_path.exists():
            continue
        try:
            with Image.open(png_path) as image:
                rgba = image.convert("RGBA")
                lower_path = png_path.as_posix().lower()
                if "leather" in lower_path:
                    pixels = rgba.load()
                    for y in range(rgba.height):
                        for x in range(rgba.width):
                            r, g, b, a = pixels[x, y]
                            if a == 0:
                                continue
                            lum = int((r + g + b) / 3)
                            if lum <= 8:
                                pixels[x, y] = (r, g, b, 0)
                            elif 96 <= lum <= 192:
                                pixels[x, y] = (128, 128, 128, a)
                            else:
                                pixels[x, y] = (255, 255, 255, a)
                rgba.save(png_path.with_suffix(".tga"))
                converted += 1
        except Exception:
            continue
    return {"armor_tga_alpha_masks": converted}


def _write_texture_sets() -> Dict[str, Any]:
    written = 0
    texture_roots = [TARGET_RP_DIR / "textures"]
    for root in texture_roots:
        if not root.exists():
            continue
        by_base: Dict[Path, Dict[str, Path]] = {}
        for texture in root.glob("**/*"):
            if not texture.is_file() or texture.suffix.lower() not in TEXTURE_EXTENSIONS:
                continue
            stem = texture.with_suffix("")
            suffix_match = None
            for suffix, channel in PBR_SUFFIXES.items():
                if stem.name.lower().endswith(suffix):
                    suffix_match = (suffix, channel)
                    break
            if suffix_match is None:
                by_base.setdefault(stem, {}).setdefault("color", texture)
                continue
            suffix, channel = suffix_match
            base = stem.with_name(stem.name[: -len(suffix)])
            by_base.setdefault(base, {})[channel] = texture

        for base, channels in by_base.items():
            # minecraft:texture_set only supports color + metalness_emissive_roughness
            # + exactly one of normal|heightmap. A standalone "emissive" texture has
            # no valid layer (emissive is the green channel of the MER map), so it is
            # NOT a reason to emit a texture set on its own.
            if not any(channel in channels for channel in ("normal", "heightmap", "mer")):
                continue
            # normal and heightmap are mutually exclusive (defining both is a
            # Bedrock CONTENT_ERROR); prefer the normal map when both are present.
            if "normal" in channels and "heightmap" in channels:
                channels.pop("heightmap", None)
            color = channels.get("color")
            if color is None:
                for ext in TEXTURE_EXTENSIONS:
                    candidate = base.with_suffix(ext)
                    if candidate.exists():
                        color = candidate
                        break
            if color is None:
                continue
            color_stem = _texture_stem_from_output(color)
            if not color_stem:
                continue
            payload: Dict[str, Any] = {"format_version": "1.16.100", "minecraft:texture_set": {"color": color_stem}}
            texture_set = payload["minecraft:texture_set"]
            channel_names = {
                "normal": "normal",
                "heightmap": "heightmap",
                "mer": "metalness_emissive_roughness",
            }
            for channel in ("normal", "heightmap", "mer"):
                source = channels.get(channel)
                if source:
                    channel_stem = _texture_stem_from_output(source)
                    if channel_stem:
                        texture_set[channel_names[channel]] = channel_stem
            _write_json(base.with_suffix(".texture_set.json"), payload)
            written += 1
    return {"texture_set_count": written}


def _atlas_key_from_texture(stem: str, prefix: str) -> str:
    raw = stem[len(prefix) :] if stem.startswith(prefix) else PurePosixPath(stem).name
    return re.sub(r"[^a-z0-9_.-]+", "_", raw.lower()).strip("_")


def _ensure_atlas_entries() -> Dict[str, Any]:
    item_path = TARGET_RP_DIR / "textures" / "item_texture.json"
    terrain_path = TARGET_RP_DIR / "textures" / "terrain_texture.json"
    item = _load_json(item_path)
    terrain = _load_json(terrain_path)
    if not isinstance(item, dict):
        item = {"resource_pack_name": "geyser_custom", "texture_name": "atlas.items", "texture_data": {}}
    if not isinstance(terrain, dict):
        terrain = {"resource_pack_name": "geyser_custom", "texture_name": "atlas.terrain", "texture_data": {}}
    item_data = item.setdefault("texture_data", {})
    terrain_data = terrain.setdefault("texture_data", {})
    if not isinstance(item_data, dict):
        item_data = {}
        item["texture_data"] = item_data
    if not isinstance(terrain_data, dict):
        terrain_data = {}
        terrain["texture_data"] = terrain_data

    added_items = 0
    added_blocks = 0
    for texture in TARGET_RP_DIR.glob("textures/items/**/*"):
        if not texture.is_file() or texture.suffix.lower() not in TEXTURE_EXTENSIONS:
            continue
        stem = _texture_stem_from_output(texture)
        if not stem:
            continue
        key = _atlas_key_from_texture(stem, "textures/items/")
        if key and key not in item_data:
            item_data[key] = {"textures": stem}
            added_items += 1
    for texture in TARGET_RP_DIR.glob("textures/blocks/**/*"):
        if not texture.is_file() or texture.suffix.lower() not in TEXTURE_EXTENSIONS:
            continue
        stem = _texture_stem_from_output(texture)
        if not stem:
            continue
        key = _atlas_key_from_texture(stem, "textures/blocks/")
        if key and key not in terrain_data:
            terrain_data[key] = {"textures": stem}
            added_blocks += 1

    _write_json(item_path, item)
    _write_json(terrain_path, terrain)
    return {"atlas_items_added": added_items, "atlas_blocks_added": added_blocks}


def _add_atlas_entry(atlas_path: Path, key: str, texture_stem: str, texture_name: str) -> bool:
    data = _load_json(atlas_path)
    if not isinstance(data, dict):
        data = {"resource_pack_name": "geyser_custom", "texture_name": texture_name, "texture_data": {}}
    data.setdefault("resource_pack_name", "geyser_custom")
    data.setdefault("texture_name", texture_name)
    texture_data = data.setdefault("texture_data", {})
    if not isinstance(texture_data, dict):
        texture_data = {}
        data["texture_data"] = texture_data
    if key in texture_data:
        return False
    texture_data[key] = {"textures": texture_stem}
    _write_json(atlas_path, data)
    return True


def _add_item_texture(key: str, texture_stem: str) -> bool:
    return _add_atlas_entry(
        TARGET_RP_DIR / "textures" / "item_texture.json",
        key,
        texture_stem,
        "atlas.items",
    )


def _add_terrain_texture(key: str, texture_stem: str) -> bool:
    return _add_atlas_entry(
        TARGET_RP_DIR / "textures" / "terrain_texture.json",
        key,
        texture_stem,
        "atlas.terrain",
    )


def _component_from_java_item(data: Dict[str, Any], icon_key: str) -> Dict[str, Any]:
    components: Dict[str, Any] = {"minecraft:icon": {"texture": icon_key}}
    component_data = data.get("components")
    if isinstance(component_data, dict):
        durability = component_data.get("minecraft:durability") or component_data.get("durability")
        if isinstance(durability, dict):
            max_damage = durability.get("max_damage") or durability.get("max_durability") or durability.get("durability")
            if isinstance(max_damage, (int, float)):
                components["minecraft:durability"] = {"max_durability": int(max_damage)}

        food = component_data.get("minecraft:food") or component_data.get("food") or component_data.get("minecraft:consumable")
        if isinstance(food, dict):
            nutrition = food.get("nutrition") or food.get("value")
            saturation = food.get("saturation_modifier") or food.get("saturation")
            converted_food: Dict[str, Any] = {}
            if isinstance(nutrition, (int, float)):
                converted_food["nutrition"] = int(nutrition)
            if isinstance(saturation, (int, float)):
                converted_food["saturation_modifier"] = float(saturation)
            if converted_food:
                components["minecraft:food"] = converted_food

        if component_data.get("minecraft:allow_off_hand") is True or component_data.get("allow_off_hand") is True:
            components["minecraft:allow_off_hand"] = True
        if component_data.get("minecraft:glint") is True or component_data.get("enchantment_glint") is True:
            components["minecraft:foil"] = True
        if component_data.get("minecraft:dyeable") is not None or component_data.get("dyeable") is not None:
            components["minecraft:dyeable"] = {}
    return components


def _generate_custom_item_components() -> Dict[str, Any]:
    generated = 0
    for item_file in _iter_files(PACK_DIR, ("assets/**/items/*.json", "assets/**/items/**/*.json")):
        data = _load_json(item_file)
        if not isinstance(data, dict):
            continue
        try:
            parts = item_file.relative_to(PACK_DIR).parts
            namespace = parts[1]
        except Exception:
            namespace = "minecraft"
        item_name = item_file.stem
        icon_key = re.sub(r"[^a-z0-9_.-]+", "_", f"{namespace}_{item_name}".lower()).strip("_")
        target = TARGET_BP_DIR / "items" / namespace / f"{item_name}.json"
        if target.exists():
            continue
        payload = {
            "format_version": "1.20.80",
            "minecraft:item": {
                "description": {"identifier": f"geyser_custom:{icon_key}", "menu_category": {"category": "items"}},
                "components": _component_from_java_item(data, icon_key),
            },
        }
        _write_json(target, payload)
        generated += 1
    return {"custom_item_component_files": generated}


def _resolve_item_icon_key(namespace: str, item_name: str) -> str:
    candidates = [
        TARGET_RP_DIR / "textures" / "items" / namespace / f"{item_name}.png",
        TARGET_RP_DIR / "textures" / "items" / f"{item_name}.png",
        TARGET_RP_DIR / "textures" / "items" / namespace / f"{item_name}.tga",
        TARGET_RP_DIR / "textures" / "items" / f"{item_name}.tga",
    ]
    for candidate in candidates:
        if candidate.exists():
            stem = _texture_stem_from_output(candidate)
            if stem:
                key = _atlas_key_from_texture(stem, "textures/items/")
                _add_item_texture(key, stem)
                return key
    return _sanitize_identifier(f"{namespace}_{item_name}")


def _generate_item_components_from_mappings() -> Dict[str, Any]:
    mapping = _load_json(TARGET_DIR / "geyser_mappings.json")
    if not isinstance(mapping, dict):
        return {"mapping_item_component_files": 0}
    items = mapping.get("items")
    if not isinstance(items, dict):
        return {"mapping_item_component_files": 0}

    generated = 0
    for item_id, entries in sorted(items.items()):
        iterable = entries if isinstance(entries, list) else [entries]
        for entry in iterable:
            if not isinstance(entry, dict):
                continue
            # Geyser v2 keeps the icon under bedrock_options.icon (a shortname KEY);
            # fall back to a legacy top-level "icon" (which may be a texture path).
            options = entry.get("bedrock_options") if isinstance(entry.get("bedrock_options"), dict) else {}
            icon = options.get("icon") or entry.get("icon")
            name = (
                entry.get("bedrock_identifier")
                or entry.get("name")
                or entry.get("model")
                or entry.get("item_model")
            )
            if not isinstance(name, str) or not name.strip():
                if isinstance(icon, str):
                    name = _atlas_key_from_texture(icon, "textures/items/")
                else:
                    digest = hashlib.md5(json.dumps(entry, sort_keys=True).encode("utf-8")).hexdigest()[:8]
                    name = f"mapped_{digest}"
            bedrock_name = _sanitize_identifier(str(name).split(":")[-1].replace("/", "_"))
            target = TARGET_BP_DIR / "items" / "geyser_custom" / f"{bedrock_name}.json"
            if target.exists():
                continue

            icon_key = bedrock_name
            if isinstance(icon, str) and icon.strip():
                if icon.startswith("textures/"):
                    # Legacy texture-path icon: register an atlas entry for it.
                    icon_key = _atlas_key_from_texture(icon, "textures/items/")
                    _add_item_texture(icon_key, icon)
                else:
                    # v2 shortname key: already registered in item_texture.json
                    # by _ensure_atlas_entries; use it directly.
                    icon_key = icon

            components: Dict[str, Any] = {
                "minecraft:icon": {"texture": icon_key},
                "minecraft:display_name": {"value": str(item_id)},
                "minecraft:allow_off_hand": bool(entry.get("allow_offhand", True)),
            }
            if str(item_id).split(":")[-1] in {"bow", "crossbow", "fishing_rod", "trident", "shield"}:
                components["minecraft:hand_equipped"] = True
            payload = {
                "format_version": "1.20.80",
                "minecraft:item": {
                    "description": {
                        "identifier": f"geyser_custom:{bedrock_name}",
                        "menu_category": {"category": "items"},
                    },
                    "components": components,
                },
            }
            _write_json(target, payload)
            generated += 1
    return {"mapping_item_component_files": generated}


def _generate_spawn_egg_textures() -> Dict[str, Any]:
    base_candidates = [
        TARGET_RP_DIR / "textures" / "items" / "spawn_egg.png",
        TARGET_RP_DIR / "textures" / "items" / "template_spawn_egg.png",
        PACK_DIR / "assets" / "minecraft" / "textures" / "item" / "template_spawn_egg.png",
        PACK_DIR / "assets" / "minecraft" / "textures" / "item" / "spawn_egg.png",
    ]
    overlay_candidates = [
        TARGET_RP_DIR / "textures" / "items" / "spawn_egg_overlay.png",
        TARGET_RP_DIR / "textures" / "items" / "template_spawn_egg_overlay.png",
        PACK_DIR / "assets" / "minecraft" / "textures" / "item" / "template_spawn_egg_overlay.png",
        PACK_DIR / "assets" / "minecraft" / "textures" / "item" / "spawn_egg_overlay.png",
    ]
    base_path = next((path for path in base_candidates if path.exists()), None)
    overlay_path = next((path for path in overlay_candidates if path.exists()), None)
    if base_path is None:
        return {"spawn_egg_textures_generated": 0}

    generated = 0
    try:
        with Image.open(base_path) as base_image:
            overlay_image = None
            if overlay_path:
                overlay_image = Image.open(overlay_path).convert("RGBA").resize(base_image.size, Image.Resampling.NEAREST)
            for entity_name, colors in SPAWN_EGG_COLORS.items():
                target = TARGET_RP_DIR / "textures" / "items" / f"{entity_name}_spawn_egg.png"
                if target.exists():
                    continue
                base_colored = _colorize_template(base_image, colors[0])
                if overlay_image is not None:
                    overlay_colored = _colorize_template(overlay_image, colors[1])
                    base_colored = _alpha_composite(base_colored, overlay_colored)
                target.parent.mkdir(parents=True, exist_ok=True)
                base_colored.save(target)
                stem = _texture_stem_from_output(target)
                if stem:
                    _add_item_texture(f"{entity_name}_spawn_egg", stem)
                generated += 1
            if overlay_image is not None:
                overlay_image.close()
    except Exception:
        return {"spawn_egg_textures_generated": generated}
    return {"spawn_egg_textures_generated": generated}


def _generate_potion_bottle_textures() -> Dict[str, Any]:
    bottle_candidates = [
        TARGET_RP_DIR / "textures" / "items" / "potion.png",
        TARGET_RP_DIR / "textures" / "items" / "potion_bottle_empty.png",
        PACK_DIR / "assets" / "minecraft" / "textures" / "item" / "potion.png",
        PACK_DIR / "assets" / "minecraft" / "textures" / "item" / "potion_bottle_empty.png",
    ]
    overlay_candidates = [
        TARGET_RP_DIR / "textures" / "items" / "potion_overlay.png",
        PACK_DIR / "assets" / "minecraft" / "textures" / "item" / "potion_overlay.png",
    ]
    bottle_path = next((path for path in bottle_candidates if path.exists()), None)
    overlay_path = next((path for path in overlay_candidates if path.exists()), None)
    if bottle_path is None:
        return {"potion_textures_generated": 0}

    generated = 0
    try:
        with Image.open(bottle_path) as bottle_image:
            overlay_image = Image.open(overlay_path).convert("RGBA").resize(bottle_image.size, Image.Resampling.NEAREST) if overlay_path else bottle_image.convert("RGBA")
            for potion_name, color in POTION_COLORS.items():
                for prefix in ("potion", "splash_potion", "lingering_potion"):
                    target = TARGET_RP_DIR / "textures" / "items" / f"{prefix}_{potion_name}.png"
                    if target.exists():
                        continue
                    colored = _colorize_template(overlay_image, color)
                    output = _alpha_composite(bottle_image, colored)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    output.save(target)
                    stem = _texture_stem_from_output(target)
                    if stem:
                        _add_item_texture(target.stem, stem)
                    generated += 1
            if overlay_path:
                overlay_image.close()
    except Exception:
        return {"potion_textures_generated": generated}
    return {"potion_textures_generated": generated}


def _generate_colormap_json() -> Dict[str, Any]:
    generated = 0
    for image_path in TARGET_RP_DIR.glob("textures/colormap/**/*"):
        if not image_path.is_file() or image_path.suffix.lower() not in TEXTURE_EXTENSIONS:
            continue
        try:
            with Image.open(image_path) as image:
                rgba = image.convert("RGBA")
                payload = {
                    "format_version": 1,
                    "source": _texture_stem_from_output(image_path),
                    "width": rgba.width,
                    "height": rgba.height,
                    "pixels": [
                        "#%02x%02x%02x%02x" % rgba.getpixel((x, y))
                        for y in range(rgba.height)
                        for x in range(rgba.width)
                    ],
                }
            _write_json(image_path.with_suffix(".colormap.json"), payload)
            generated += 1
        except Exception:
            continue
    return {"colormap_json_generated": generated}


def _generate_font_pua_item_remap() -> Dict[str, Any]:
    font_map = _load_json(TARGET_DIR / "font_map.json")
    item_atlas = _load_json(TARGET_RP_DIR / "textures" / "item_texture.json")
    if not isinstance(font_map, dict) or not isinstance(item_atlas, dict):
        return {"font_pua_item_remaps": 0}
    glyph_map = font_map.get("glyph_map")
    texture_data = item_atlas.get("texture_data")
    if not isinstance(glyph_map, dict) or not isinstance(texture_data, dict):
        return {"font_pua_item_remaps": 0}

    remaps: Dict[str, Dict[str, Any]] = {}
    generated = 0
    for key, glyph in glyph_map.items():
        if not isinstance(glyph, dict):
            continue
        codepoint = glyph.get("codepoint")
        if not isinstance(codepoint, int) or not (0xE000 <= codepoint <= 0xF8FF):
            continue
        texture = glyph.get("texture")
        slot = glyph.get("slot")
        if not isinstance(texture, str) or not isinstance(slot, list) or len(slot) != 2:
            continue
        source = TARGET_RP_DIR / f"{texture}.png"
        if not source.exists():
            continue
        try:
            with Image.open(source) as sheet:
                cell_w = sheet.width // 16
                cell_h = sheet.height // 16
                if cell_w <= 0 or cell_h <= 0:
                    continue
                x = int(slot[0]) * cell_w
                y = int(slot[1]) * cell_h
                tile = sheet.crop((x, y, x + cell_w, y + cell_h)).convert("RGBA")
                if tile.getbbox() is None:
                    continue
                out_key = f"font_pua_{codepoint:04x}"
                output = TARGET_RP_DIR / "textures" / "items" / "font_pua" / f"{out_key}.png"
                output.parent.mkdir(parents=True, exist_ok=True)
                tile.save(output)
                stem = _texture_stem_from_output(output)
                if stem:
                    texture_data[out_key] = {"textures": stem}
                    remaps[f"U+{codepoint:04X}"] = {
                        "item": f"geyser_custom:{out_key}",
                        "texture": stem,
                        "advance": glyph.get("advance"),
                        "width": glyph.get("width"),
                    }
                    generated += 1
        except Exception:
            continue

    if generated:
        _write_json(TARGET_RP_DIR / "textures" / "item_texture.json", item_atlas)
        _write_json(TARGET_DIR / "reports" / "font_pua_item_remap.json", remaps)
    return {"font_pua_item_remaps": generated}


def _ensure_blocks_json() -> Dict[str, Any]:
    blocks_json_path = TARGET_RP_DIR / "blocks.json"
    blocks_data = _load_json(blocks_json_path)
    if not isinstance(blocks_data, dict):
        blocks_data = {}
    added = 0

    terrain = _load_json(TARGET_RP_DIR / "textures" / "terrain_texture.json")
    texture_data = terrain.get("texture_data") if isinstance(terrain, dict) else {}
    if isinstance(texture_data, dict):
        for key in sorted(texture_data):
            if key.startswith("gmdl_atlas_"):
                continue
            identifier = f"geyser_custom:{_sanitize_identifier(key)}"
            if identifier in blocks_data:
                continue
            blocks_data[identifier] = {"textures": key, "sound": "stone"}
            added += 1

    if added:
        _write_json(blocks_json_path, blocks_data)
    return {"blocks_json_entries_added": added, "blocks_json_entry_count": len(blocks_data)}


def _custom_namespace_prefixes() -> Set[str]:
    namespaces: Set[str] = set()
    assets_dir = PACK_DIR / "assets"
    if not assets_dir.exists():
        return namespaces
    for child in assets_dir.iterdir():
        if child.is_dir() and child.name != "minecraft":
            namespaces.add(_sanitize_identifier(child.name))
    return namespaces


def _is_custom_terrain_key(key: str, custom_prefixes: Set[str]) -> bool:
    if os.getenv("GENERATE_ALL_BP_BLOCKS", "").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    return any(key == prefix or key.startswith(prefix + "_") for prefix in custom_prefixes)


def _ensure_block_bp_definitions() -> Dict[str, Any]:
    terrain = _load_json(TARGET_RP_DIR / "textures" / "terrain_texture.json")
    texture_data = terrain.get("texture_data") if isinstance(terrain, dict) else {}
    if not isinstance(texture_data, dict):
        return {"bp_block_files_generated": 0}

    generated = 0
    material = os.getenv("BLOCK_MATERIAL", "alpha_test").strip() or "alpha_test"
    for key in sorted(texture_data):
        if key.startswith("gmdl_atlas_"):
            continue
        safe_key = _sanitize_identifier(key)
        target = TARGET_BP_DIR / "blocks" / "geyser_custom" / f"{safe_key}.json"
        if target.exists():
            continue
        payload = {
            "format_version": "1.20.80",
            "minecraft:block": {
                "description": {"identifier": f"geyser_custom:{safe_key}"},
                "components": {
                    "minecraft:material_instances": {
                        "*": {"texture": key, "render_method": material}
                    },
                    "minecraft:geometry": "minecraft:geometry.full_block",
                    "minecraft:light_dampening": 15,
                    "minecraft:collision_box": True,
                    "minecraft:selection_box": True,
                },
            },
        }
        _write_json(target, payload)
        generated += 1
    return {"bp_block_files_generated": generated}


def _ensure_material_files() -> Dict[str, Any]:
    materials_dir = TARGET_RP_DIR / "materials"
    materials_dir.mkdir(parents=True, exist_ok=True)
    material_path = materials_dir / "entity.material"
    if material_path.exists():
        return {"material_files_generated": 0}
    material_path.write_text(
        "materials {\n"
        "  version 1\n"
        "  entity_emissive_alpha_one_sided:entity_alphatest_one_sided {\n"
        "    +defines = [EMISSIVE]\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    return {"material_files_generated": 1}


def _ensure_item_state_controllers() -> Dict[str, Any]:
    generated = 0
    render_dir = TARGET_RP_DIR / "render_controllers"
    anim_dir = TARGET_RP_DIR / "animations"
    controller_dir = TARGET_RP_DIR / "animation_controllers"
    render_dir.mkdir(parents=True, exist_ok=True)
    anim_dir.mkdir(parents=True, exist_ok=True)
    controller_dir.mkdir(parents=True, exist_ok=True)

    render_payload = {
        "format_version": "1.10.0",
        "render_controllers": {
            "controller.render.geyser_custom.item_states": {
                "geometry": "Geometry.default",
                "materials": [{"*": "Material.default"}],
                "textures": ["Texture.default"],
            }
        },
    }
    render_path = render_dir / "geyser_custom.item_states.render_controllers.json"
    if not render_path.exists():
        _write_json(render_path, render_payload)
        generated += 1

    animation_payload = {
        "format_version": "1.8.0",
        "animations": {
            "animation.geyser_custom.bow_pulling": {"loop": True, "bones": {}},
            "animation.geyser_custom.crossbow_charging": {"loop": True, "bones": {}},
            "animation.geyser_custom.fishing_rod_cast": {"loop": True, "bones": {}},
            "animation.geyser_custom.trident_throw": {"loop": False, "bones": {}},
        },
    }
    animation_path = anim_dir / "geyser_custom.item_states.animation.json"
    if not animation_path.exists():
        _write_json(animation_path, animation_payload)
        generated += 1

    controller_payload = {
        "format_version": "1.10.0",
        "animation_controllers": {
            "controller.animation.geyser_custom.item_states": {
                "states": {
                    "default": {
                        "animations": [
                            {"bow_pulling": "query.is_using_item && query.get_equipped_item_name == 'bow'"},
                            {"crossbow_charging": "query.is_using_item && query.get_equipped_item_name == 'crossbow'"},
                            {"fishing_rod_cast": "query.is_using_item && query.get_equipped_item_name == 'fishing_rod'"},
                            {"trident_throw": "query.is_using_item && query.get_equipped_item_name == 'trident'"},
                        ]
                    }
                }
            }
        },
    }
    controller_path = controller_dir / "geyser_custom.item_states.animation_controllers.json"
    if not controller_path.exists():
        _write_json(controller_path, controller_payload)
        generated += 1

    return {"item_state_controller_files": generated}


def _ensure_gui_hud_placeholder() -> Dict[str, Any]:
    # BUG FIX: Do NOT write a custom ui/hud_screen.json.
    #
    # Writing ANY hud_screen.json without declaring ALL vanilla HUD controls
    # (health bar, hunger bar, armor bar, hotbar, XP bar, etc.) completely
    # replaces Bedrock's built-in HUD with whatever controls are listed.
    # The previous implementation wrote an almost-empty panel which caused
    # the hunger bar, armor bar, and hotbar to become invisible in MC PE.
    #
    # Java GUI textures are still copied to textures/gui/ for direct texture
    # replacement (e.g., textures/gui/minecraft/gui/icons.png).  That works
    # fine without overriding the UI JSON.  Removing hud_screen.json lets
    # Bedrock use its own default HUD layout with our custom textures applied.
    #
    # If you need to add truly custom HUD overlays in the future, write a
    # hud_screen.json that EXTENDS the vanilla namespace and only adds new
    # controls — never remove or replace existing vanilla control bindings.

    # Cleanup: remove any stale hud_screen.json left over from a previous run
    # so it doesn't silently re-break the HUD on the next conversion.
    stale_hud = TARGET_RP_DIR / "ui" / "hud_screen.json"
    if stale_hud.exists():
        stale_hud.unlink()
        _log("Removed stale ui/hud_screen.json (was hiding Bedrock HUD elements)")
        ui_dir = TARGET_RP_DIR / "ui"
        try:
            if ui_dir.is_dir() and not any(ui_dir.iterdir()):
                ui_dir.rmdir()
        except OSError:
            pass

    return {"hud_screen_files": 0}


def _shorten_long_paths() -> Dict[str, Any]:
    """Rename files whose RP-relative paths are >= 80 chars to stay within Bedrock's limit.

    Bedrock (and GeyserMC) emit WARN for every file path that is >= 80 characters.
    On some Bedrock platforms (console, certain mobile builds) these files fail to
    load entirely.  This function:
      1. Finds every file in TARGET_RP_DIR whose relative path length >= 80.
      2. Derives a shorter path by abbreviating intermediate directory components.
      3. Moves the file to the new path.
      4. Scans every *.json / *.lang / *.material file in the pack and replaces
         all occurrences of the old path (with and without extension) with the
         new path.

    The abbreviation strategy keeps the first two directory levels intact
    (e.g. "textures/items") and compresses deeper levels to their first three
    characters, joined with underscores.  A four-character MD5 suffix is appended
    to the stem when the filename itself is still too long after shortening dirs.
    """
    MAX_LEN = 79  # Bedrock hard limit is 80, so we target <= 79

    # ── 1. Collect files that need renaming ─────────────────────────────────
    rename_map: Dict[str, str] = {}   # old_rel → new_rel  (POSIX, no leading /)

    for fpath in sorted(TARGET_RP_DIR.rglob("*")):
        if not fpath.is_file():
            continue
        try:
            rel = fpath.relative_to(TARGET_RP_DIR).as_posix()
        except ValueError:
            continue
        if len(rel) < 80:
            continue

        parts = rel.split("/")
        filename = parts[-1]
        dir_parts = parts[:-1]
        ext = Path(filename).suffix
        stem = Path(filename).stem

        # Build short directory prefix
        if len(dir_parts) <= 2:
            short_dir = "/".join(dir_parts)
        else:
            base = "/".join(dir_parts[:2])
            abbrev = "_".join(p[:3].rstrip("_-") for p in dir_parts[2:] if p)
            short_dir = f"{base}/{abbrev}" if abbrev else base

        # Check if filename alone fits
        max_stem_len = MAX_LEN - len(short_dir) - 1 - len(ext)  # -1 for "/"
        if max_stem_len < 6:
            # Extreme case: use pure hash as filename
            h = hashlib.md5(rel.encode()).hexdigest()[:12]
            new_filename = h + ext
        elif len(stem) > max_stem_len:
            # Truncate stem + 4-char hash to disambiguate
            h4 = hashlib.md5(rel.encode()).hexdigest()[:4]
            new_filename = stem[: max(1, max_stem_len - 4)] + h4 + ext
        else:
            new_filename = filename

        new_rel = f"{short_dir}/{new_filename}"

        # Guard against collisions from different sources mapping to the same target
        if new_rel in rename_map.values() and new_rel != rel:
            h6 = hashlib.md5(rel.encode()).hexdigest()[:6]
            new_filename = stem[:max(1, MAX_LEN - len(short_dir) - 1 - len(ext) - 6)] + h6 + ext
            new_rel = f"{short_dir}/{new_filename}"

        if new_rel != rel and len(new_rel) < 80:
            rename_map[rel] = new_rel

    if not rename_map:
        return {"path_renames": 0}

    _log(f"Shortening {len(rename_map)} paths that exceed 79 characters")

    # ── 2. Move the files ────────────────────────────────────────────────────
    for old_rel, new_rel in rename_map.items():
        old_path = TARGET_RP_DIR / old_rel
        new_path = TARGET_RP_DIR / new_rel
        if not old_path.exists():
            continue
        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_path), str(new_path))

    # Clean up now-empty intermediate directories
    for old_rel in rename_map:
        parent = (TARGET_RP_DIR / old_rel).parent
        for _ in range(5):          # walk up at most 5 levels
            if parent == TARGET_RP_DIR:
                break
            try:
                if parent.is_dir() and not any(parent.iterdir()):
                    parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    # ── 3. Patch JSON / lang / material references ───────────────────────────
    # Build two lookup tables: with-extension and without-extension versions
    ext_map: Dict[str, str] = {}
    noext_map: Dict[str, str] = {}
    for old_rel, new_rel in rename_map.items():
        ext_map[old_rel] = new_rel
        # Strip common texture extensions for JSON references like "textures/items/foo"
        for tex_ext in (".png", ".tga", ".jpg", ".jpeg"):
            if old_rel.lower().endswith(tex_ext):
                old_noext = old_rel[: -len(tex_ext)]
                new_noext = new_rel[: -len(tex_ext)]
                noext_map[old_noext] = new_noext
                break

    patchable_suffixes = {".json", ".lang", ".material", ".mcmeta"}
    patched_files = 0

    for fpath in TARGET_RP_DIR.rglob("*"):
        if not fpath.is_file():
            continue
        if fpath.suffix.lower() not in patchable_suffixes:
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
            try:
                fpath.write_text(text, encoding="utf-8")
                patched_files += 1
            except Exception:
                pass

    _log(f"Path shortening done: {len(rename_map)} files renamed, {patched_files} JSON/lang files patched")
    return {"path_renames": len(rename_map), "path_patch_files": patched_files}


def _ensure_displayentity_placeholders() -> Dict[str, Any]:
    signals = list(_iter_files(PACK_DIR, ("assets/**/display*/**/*", "**/*display_entity*.*", "**/*displayentity*.*")))
    if not signals:
        return {"display_entity_placeholders": 0}
    geo_dir = TARGET_RP_DIR / "models" / "entity"
    entity_dir = TARGET_RP_DIR / "entity"
    geo_dir.mkdir(parents=True, exist_ok=True)
    entity_dir.mkdir(parents=True, exist_ok=True)
    geo_path = geo_dir / "display_entity_armor_stand.geo.json"
    entity_path = entity_dir / "display_entity_armor_stand.entity.json"
    generated = 0
    if not geo_path.exists():
        _write_json(
            geo_path,
            {
                "format_version": "1.12.0",
                "minecraft:geometry": [
                    {
                        "description": {
                            "identifier": "geometry.geyser_custom.display_entity_armor_stand",
                            "texture_width": 16,
                            "texture_height": 16,
                            "visible_bounds_width": 2,
                            "visible_bounds_height": 2,
                            "visible_bounds_offset": [0, 1, 0],
                        },
                        "bones": [{"name": "root", "pivot": [0, 0, 0], "cubes": []}],
                    }
                ],
            },
        )
        generated += 1
    if not entity_path.exists():
        _write_json(
            entity_path,
            {
                "format_version": "1.10.0",
                "minecraft:client_entity": {
                    "description": {
                        "identifier": "geyser_custom:display_entity_armor_stand",
                        "materials": {"default": "entity_alphatest"},
                        "textures": {"default": "textures/items/barrier"},
                        "geometry": {"default": "geometry.geyser_custom.display_entity_armor_stand"},
                        "render_controllers": ["controller.render.default"],
                    }
                },
            },
        )
        generated += 1
    return {"display_entity_placeholders": generated}


def _ensure_modelengine_placeholders() -> Dict[str, Any]:
    signals = list(_iter_files(PACK_DIR, ("**/*modelengine*/*", "**/*model_engine*/*", "**/*.bbmodel")))
    if not signals:
        return {"modelengine_placeholder_files": 0}
    geo_dir = TARGET_RP_DIR / "models" / "entity" / "modelengine"
    controller_dir = TARGET_RP_DIR / "animation_controllers"
    geo_dir.mkdir(parents=True, exist_ok=True)
    controller_dir.mkdir(parents=True, exist_ok=True)
    generated = 0
    for source in signals[:100]:
        safe = _sanitize_identifier(source.stem)
        geo_path = geo_dir / f"{safe}.geo.json"
        if geo_path.exists():
            continue
        _write_json(
            geo_path,
            {
                "format_version": "1.12.0",
                "minecraft:geometry": [
                    {
                        "description": {
                            "identifier": f"geometry.geyser_custom.modelengine.{safe}",
                            "texture_width": 64,
                            "texture_height": 64,
                            "visible_bounds_width": 4,
                            "visible_bounds_height": 4,
                            "visible_bounds_offset": [0, 1, 0],
                        },
                        "bones": [{"name": "root", "pivot": [0, 0, 0], "cubes": []}],
                    }
                ],
            },
        )
        generated += 1
    controller_path = controller_dir / "modelengine.animation_controllers.json"
    if not controller_path.exists():
        _write_json(
            controller_path,
            {
                "format_version": "1.10.0",
                "animation_controllers": {
                    "controller.animation.geyser_custom.modelengine": {"states": {"default": {}}}
                },
            },
        )
        generated += 1
    return {"modelengine_placeholder_files": generated}


def _ensure_furniture_behavior_pack() -> Dict[str, Any]:
    plugin_context = _load_json(STAGING_DIR / "plugin_context.json")
    detected = plugin_context.get("detected_plugins") if isinstance(plugin_context, dict) else []
    if not isinstance(detected, list) or not any(name in detected for name in ("itemadder", "oraxen", "nexo", "craftengine")):
        return {"furniture_bp_files": 0}

    generated = 0
    for source in _iter_files(PACK_DIR, ("**/*.json", "**/*.yml", "**/*.yaml")):
        low = source.as_posix().lower()
        if not any(token in low for token in ("furniture", "chairs", "decor", "itemsadder", "oraxen", "nexo", "craftengine")):
            continue
        safe = _sanitize_identifier(source.stem)
        target = TARGET_BP_DIR / "entities" / "geyser_custom" / f"{safe}_furniture.json"
        if target.exists():
            continue
        payload = {
            "format_version": "1.20.80",
            "minecraft:entity": {
                "description": {
                    "identifier": f"geyser_custom:{safe}_furniture",
                    "is_spawnable": False,
                    "is_summonable": True,
                    "is_experimental": False,
                },
                "components": {
                    "minecraft:type_family": {"family": ["geyser_custom_furniture"]},
                    "minecraft:collision_box": {"width": 1.0, "height": 1.0},
                    "minecraft:physics": {},
                    "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
                },
            },
        }
        _write_json(target, payload)
        generated += 1
        if generated >= 200:
            break
    return {"furniture_bp_files": generated}


def _ensure_sound_definitions() -> Dict[str, Any]:
    sounds_dir = TARGET_RP_DIR / "sounds"
    sound_definitions_path = sounds_dir / "sound_definitions.json"
    payload = _load_json(sound_definitions_path)
    if not isinstance(payload, dict):
        payload = {"format_version": "1.14.0", "sound_definitions": {}}
    definitions = payload.setdefault("sound_definitions", {})
    if not isinstance(definitions, dict):
        definitions = {}
        payload["sound_definitions"] = definitions
    added = 0
    for sound_file in sounds_dir.glob("**/*"):
        if not sound_file.is_file() or sound_file.suffix.lower() not in {".ogg", ".wav", ".mp3", ".flac"}:
            continue
        rel = sound_file.relative_to(sounds_dir).as_posix()
        event_name = _sanitize_identifier(rel.rsplit(".", 1)[0].replace("/", "."))
        sound_ref = f"sounds/{rel.rsplit('.', 1)[0]}"
        if event_name not in definitions:
            definitions[event_name] = {"sounds": [{"name": sound_ref, "stream": False}]}
            added += 1
    _write_json(sound_definitions_path, payload)
    return {"sound_definition_entries_added": added, "sound_definition_entry_count": len(definitions)}


def _sanitize_geyser_mappings() -> Dict[str, Any]:
    mapping_path = TARGET_DIR / "geyser_mappings.json"
    mapping = _load_json(mapping_path)
    if not isinstance(mapping, dict):
        return {"geyser_mapping_sanitized": False}

    items = mapping.get("items")
    if not isinstance(items, dict):
        return {"geyser_mapping_sanitized": False}

    clean_items: Dict[str, List[Dict[str, Any]]] = {}
    skipped: List[Dict[str, str]] = []
    removed_entries = 0
    duplicate_entries = 0
    allow_custom_registry = _allow_custom_java_items()

    for raw_item_id, raw_entries in sorted(items.items()):
        canonical_item = _canonical_java_item_key(raw_item_id, allow_custom_path=allow_custom_registry)
        if not canonical_item or not _known_java_item_key(canonical_item):
            entry_count = len(raw_entries) if isinstance(raw_entries, list) else 1
            removed_entries += entry_count
            skipped.append({"item": str(raw_item_id), "reason": "unknown_java_item"})
            continue

        entries = raw_entries if isinstance(raw_entries, list) else [raw_entries]
        clean_entries: List[Dict[str, Any]] = []
        seen: Set[Tuple[Any, Any, Any, Any, Any]] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                removed_entries += 1
                skipped.append({"item": canonical_item, "reason": "invalid_entry"})
                continue
            if not _mapping_entry_has_predicate(entry) and not (
                allow_custom_registry and str(entry.get("type", "")).strip().lower() == "definition"
            ):
                removed_entries += 1
                skipped.append({"item": canonical_item, "reason": "missing_custom_model_predicate"})
                continue

            name = entry.get("name") or entry.get("bedrock_identifier") or entry.get("icon")
            key = (
                name,
                entry.get("custom_model_data"),
                entry.get("damage_predicate"),
                entry.get("unbreakable"),
                entry.get("icon"),
            )
            if key in seen:
                duplicate_entries += 1
                continue
            seen.add(key)
            clean_entries.append(entry)

        if clean_entries:
            clean_items.setdefault(canonical_item, []).extend(clean_entries)

    mapping["items"] = clean_items
    metadata = mapping.setdefault("metadata", {})
    if isinstance(metadata, dict):
        metadata["sanitized_by"] = "bedrock_post.py"
        metadata["removed_entry_count"] = removed_entries
        metadata["duplicate_entry_count"] = duplicate_entries
        metadata["skipped_item_count"] = len(skipped)
        metadata["skipped_items"] = skipped[:500]
    _write_json(mapping_path, mapping)
    _write_json(
        TARGET_DIR / "reports" / "geyser_mapping_validation.json",
        {
            "status": "pass" if not removed_entries and not duplicate_entries else "sanitized",
            "remaining_item_count": len(clean_items),
            "remaining_entry_count": sum(len(value) for value in clean_items.values()),
            "removed_entry_count": removed_entries,
            "duplicate_entry_count": duplicate_entries,
            "skipped_item_count": len(skipped),
            "skipped_items": skipped[:500],
        },
    )
    return {
        "geyser_mapping_sanitized": bool(removed_entries or duplicate_entries),
        "geyser_mapping_remaining_items": len(clean_items),
        "geyser_mapping_remaining_entries": sum(len(value) for value in clean_items.values()),
        "geyser_mapping_removed_entries": removed_entries,
        "geyser_mapping_duplicate_entries": duplicate_entries,
    }


def _write_conversion_validation() -> Dict[str, Any]:
    missing: List[str] = []
    json_errors: List[str] = []
    for root in (TARGET_RP_DIR, TARGET_BP_DIR):
        if not root.exists():
            continue
        for json_path in root.glob("**/*.json"):
            if not _is_json_valid(json_path):
                try:
                    json_errors.append(json_path.relative_to(TARGET_DIR).as_posix())
                except Exception:
                    json_errors.append(json_path.as_posix())

    for atlas_rel in ("textures/item_texture.json", "textures/terrain_texture.json"):
        atlas_path = TARGET_RP_DIR / atlas_rel
        atlas = _load_json(atlas_path)
        texture_data = atlas.get("texture_data") if isinstance(atlas, dict) else {}
        if not isinstance(texture_data, dict):
            missing.append(f"{atlas_rel}:missing_texture_data")
            continue
        for key, entry in texture_data.items():
            values = entry.get("textures") if isinstance(entry, dict) else entry
            texture_values = values if isinstance(values, list) else [values]
            for value in texture_values:
                if not isinstance(value, str):
                    missing.append(f"{atlas_rel}:{key}:invalid")
                    continue
                stem = value.replace("\\", "/").strip("/")
                if not any((TARGET_RP_DIR / f"{stem}{ext}").exists() for ext in TEXTURE_EXTENSIONS):
                    missing.append(f"{atlas_rel}:{key}:{stem}")

    payload = {
        "status": "pass" if not missing and not json_errors else "needs_review",
        "missing_texture_count": len(missing),
        "invalid_json_count": len(json_errors),
        "missing_textures": sorted(set(missing))[:500],
        "invalid_json": sorted(set(json_errors))[:500],
    }
    _write_json(TARGET_DIR / "reports" / "bedrock_validation_report.json", payload)
    return {
        "validation_status": payload["status"],
        "validation_missing_texture_count": payload["missing_texture_count"],
        "validation_invalid_json_count": payload["invalid_json_count"],
    }


def _safe_unlink(path: Path) -> bool:
    try:
        path.unlink()
        return True
    except OSError:
        return False


def _detect_unsupported() -> Dict[str, Any]:
    warnings: List[Dict[str, str]] = []
    for key, (pattern, message) in UNSUPPORTED_HINTS.items():
        matches = list(_iter_files(PACK_DIR, (pattern,)))
        if matches:
            warnings.append({"feature": key, "count": str(len(matches)), "message": message})

    version_note = os.getenv("DEFAULT_ASSET_VERSION", os.getenv("DEFAULT_ASSETS_VERSION", "")).strip()
    if version_note == "1.26.1.2":
        warnings.append(
            {
                "feature": "version_alias",
                "count": "1",
                "message": "Input version corrected: use 26.1.2, not 1.26.1.2.",
            }
        )
    if version_note == "26.1.2":
        warnings.append(
            {
                "feature": "version_alias",
                "count": "1",
                "message": "26.1.2 is preserved as a requested resource-pack asset version label; no 1.x prefix is assumed.",
            }
        )

    return {"unsupported_warning_count": len(warnings), "warnings": warnings}


def _sanitize_output_files() -> Dict[str, Any]:
    removed = 0
    allowed = {
        ".json",
        ".png",
        ".tga",
        ".jpg",
        ".jpeg",
        ".lang",
        ".material",
        ".txt",
        ".bin",
        ".ogg",
        ".wav",
        ".mp3",
        ".flac",
    }
    for root in (TARGET_RP_DIR, TARGET_BP_DIR):
        if not root.exists():
            continue
        for path in list(root.rglob("*")):
            if not path.is_file():
                continue
            if path.name.lower() in {"thumbs.db", ".ds_store"}:
                if _safe_unlink(path):
                    removed += 1
                continue
            if path.suffix.lower() == ".mcmeta":
                if _safe_unlink(path):
                    removed += 1
                continue
            if path.suffix and path.suffix.lower() not in allowed:
                if "imported_java" in path.parts:
                    continue
                if _safe_unlink(path):
                    removed += 1
    removed_dirs = 0
    for root in (TARGET_RP_DIR, TARGET_BP_DIR):
        if not root.exists():
            continue
        for directory in sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            try:
                directory.rmdir()
                removed_dirs += 1
            except OSError:
                continue
    return {"post_removed_files": removed, "post_removed_empty_dirs": removed_dirs}


def run() -> None:
    TARGET_RP_DIR.mkdir(parents=True, exist_ok=True)
    TARGET_BP_DIR.mkdir(parents=True, exist_ok=True)
    (TARGET_DIR / "reports").mkdir(parents=True, exist_ok=True)

    rp_uuid = _ensure_manifest(TARGET_RP_DIR / "manifest.json", "resources", "RP")
    _ensure_manifest(TARGET_BP_DIR / "manifest.json", "data", "BP", dependency_uuid=rp_uuid)

    report: Dict[str, Any] = {}
    report["pack_icon_rp"] = _ensure_pack_icon(TARGET_RP_DIR)
    report["pack_icon_bp"] = _ensure_pack_icon(TARGET_BP_DIR)
    report.update(_copy_java_texture_tree())
    report.update(_convert_lang_files())
    report.update(_convert_mcmeta_flipbooks())
    report.update(_split_emissive_and_transparency())
    report.update(_convert_png_to_tga_for_alpha_masks())
    report.update(_write_texture_sets())
    report.update(_ensure_atlas_entries())
    report.update(_generate_custom_item_components())
    report.update(_sanitize_geyser_mappings())
    report.update(_generate_item_components_from_mappings())
    report.update(_generate_spawn_egg_textures())
    report.update(_generate_potion_bottle_textures())
    report.update(_generate_colormap_json())
    report.update(_generate_font_pua_item_remap())
    report.update(_ensure_blocks_json())
    report.update(_ensure_block_bp_definitions())
    report.update(_ensure_material_files())
    report.update(_ensure_item_state_controllers())
    report.update(_ensure_gui_hud_placeholder())
    report.update(_ensure_displayentity_placeholders())
    report.update(_ensure_modelengine_placeholders())
    report.update(_ensure_furniture_behavior_pack())
    report.update(_ensure_sound_definitions())
    report.update(_detect_unsupported())
    report.update(_write_conversion_validation())
    report.update(_sanitize_output_files())
    # Shorten any paths that are >= 80 chars (GeyserMC WARN + some Bedrock platforms reject them)
    report.update(_shorten_long_paths())

    _write_json(REPORT_FILE, report)
    _log(f"Post-processing complete: {REPORT_FILE}")


if __name__ == "__main__":
    run()
