from __future__ import annotations

import copy
import re
from collections import Counter, defaultdict
from typing import Any

from cs2_skins_api.constants import (
    CONTAINER_PREFABS,
    HANDLED_TOP_LEVEL_BLOCKS,
    STANDARD_EXTERIORS,
    STICKER_FINISH_ORDER,
    WEAPON_GROUPS,
)
from cs2_skins_api.utils import deep_merge, parse_float, parse_int, slugify, unique_list


LEAF_ENTRY_RE = re.compile(r"^\[(?P<token>[^\]]+)\](?P<target>[A-Za-z0-9_]+)$")
SIGNATURE_PACK_RE = re.compile(r"^crate_signature_pack_(?P<event>[a-z0-9]+)_(?P<suffix>.+)$")
EVENT_SLUG_TOKEN_RE = re.compile(r"^[a-z]+[0-9]{2,4}$")
EVENT_NAME_RE = re.compile(r"([A-Z0-9][A-Za-z0-9'&.+-]*(?: [A-Z0-9][A-Za-z0-9'&.+-]*)* (?:19|20)\d{2})")
AGGREGATE_LOOT_TIERS = ("uncommon", "rare", "mythical", "legendary", "ancient")
IGNORED_LOOT_ENTRIES = {
    "public_list_contents",
    "contains_stickers_representing_organizations",
    "contains_patches_representing_organizations",
    "contains_stickers_autographed_by_proplayers",
    "limit_description_to_number_rnd",
}
ITEM_ASSET_KEYS = (
    "image_inventory",
    "image_unusual_item",
    "icon_default_image",
    "inventory_image_section",
    "inventory_image_data",
    "model_player",
    "model_world",
    "model_ag2",
    "pedestal_display_model",
    "display_seed",
)


class Localizer:
    def __init__(self, tokens_by_locale: dict[str, dict[str, str]], default_locale: str = "english") -> None:
        self.tokens_by_locale = tokens_by_locale
        self.default_locale = default_locale

    def resolve(self, token: str | None, locale: str | None = None) -> str | None:
        if token is None:
            return None
        if not isinstance(token, str):
            return str(token)
        if not token.startswith("#"):
            return token
        locale_key = locale or self.default_locale
        normalized = token[1:]
        candidate = self.tokens_by_locale.get(locale_key, {}).get(normalized)
        if candidate is not None:
            return candidate
        fallback = self.tokens_by_locale.get(self.default_locale, {}).get(normalized)
        return fallback


def most_common_nonempty(values: list[str | None]) -> str | None:
    filtered = [value.strip() for value in values if isinstance(value, str) and value.strip()]
    if not filtered:
        return None
    return Counter(filtered).most_common(1)[0][0]


def split_pipe_name(value: str | None) -> tuple[str | None, str | None]:
    if not value or "|" not in value:
        return None, None
    left, right = value.rsplit("|", 1)
    return left.strip() or None, right.strip() or None


def extract_event_display_candidate(value: str | None) -> str | None:
    left, right = split_pipe_name(value)
    if right:
        return right
    if not value:
        return None
    match = EVENT_NAME_RE.search(value)
    if match:
        return match.group(1).strip()
    return None


def extract_event_slug_from_codename(value: str | None) -> str | None:
    if not value:
        return None
    for token in str(value).split("_"):
        if EVENT_SLUG_TOKEN_RE.match(token):
            return token
    return None


def extract_item_asset_refs(resolved: dict[str, Any]) -> dict[str, Any]:
    refs = {}
    for key in ITEM_ASSET_KEYS:
        value = resolved.get(key)
        if value in (None, "", {}):
            continue
        refs[key] = value

    width = parse_int(resolved.get("image_inventory_size_w"))
    height = parse_int(resolved.get("image_inventory_size_h"))
    if width is not None or height is not None:
        refs["image_inventory_size"] = {
            "w": width,
            "h": height,
        }
    return refs


def normalize_dob(value: str | None) -> str | None:
    if not value or value == "1970-01-01":
        return None
    return value


def resolve_prefabs(prefabs_raw: dict[str, dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]]]:
    resolved_cache: dict[str, dict[str, Any]] = {}
    chain_cache: dict[str, list[str]] = {}

    def resolve_one(name: str, stack: set[str]) -> tuple[dict[str, Any], list[str]]:
        if name in resolved_cache:
            return resolved_cache[name], chain_cache[name]
        if name in stack:
            raise ValueError(f"Cyclic prefab reference detected for {name}")
        stack.add(name)

        raw = prefabs_raw.get(name, {})
        merged: dict[str, Any] = {}
        chain: list[str] = []
        parents = str(raw.get("prefab", "")).split()
        for parent in parents:
            parent_resolved, parent_chain = resolve_one(parent, stack)
            merged = deep_merge(merged, parent_resolved)
            for step in parent_chain:
                if step not in chain:
                    chain.append(step)

        for key, value in raw.items():
            if key == "prefab":
                continue
            if isinstance(merged.get(key), dict) and isinstance(value, dict):
                merged[key] = deep_merge(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)

        chain.append(name)
        resolved_cache[name] = merged
        chain_cache[name] = chain
        stack.remove(name)
        return merged, chain

    for prefab_name in prefabs_raw:
        resolve_one(prefab_name, set())

    return resolved_cache, chain_cache


def resolve_item_definitions(
    items_raw: dict[str, dict[str, Any]],
    prefabs_resolved: dict[str, dict[str, Any]],
    prefab_chains: dict[str, list[str]],
) -> tuple[dict[str, dict[str, Any]], Counter[str]]:
    resolved_items: dict[str, dict[str, Any]] = {}
    prefab_usage: Counter[str] = Counter()

    for item_id, raw_item in items_raw.items():
        prefab_spec = str(raw_item.get("prefab", "")).strip()
        merged: dict[str, Any] = {}
        chain: list[str] = []
        for prefab_name in prefab_spec.split():
            if prefab_name not in prefabs_resolved:
                continue
            merged = deep_merge(merged, prefabs_resolved[prefab_name])
            for step in prefab_chains.get(prefab_name, []):
                if step not in chain:
                    chain.append(step)
        merged = deep_merge(merged, raw_item)
        classification = classify_item(raw_item, merged, chain)
        resolved_items[item_id] = {
            "id": parse_int(item_id),
            "game_id": parse_int(item_id),
            "name": raw_item.get("name"),
            "prefab_spec": prefab_spec or None,
            "prefab_chain": chain,
            "classification": classification,
            "resolved": merged,
        }
        if prefab_spec:
            prefab_usage[prefab_spec] += 1

    return resolved_items, prefab_usage


def classify_item(raw_item: dict[str, Any], resolved: dict[str, Any], prefab_chain: list[str]) -> dict[str, Any]:
    name = str(raw_item.get("name", ""))
    tool = resolved.get("tool") if isinstance(resolved.get("tool"), dict) else {}
    attributes = resolved.get("attributes") if isinstance(resolved.get("attributes"), dict) else {}
    tags = raw_item.get("tags") if isinstance(raw_item.get("tags"), dict) else {}
    prefab_tokens = set(prefab_chain + str(raw_item.get("prefab", "")).split())

    if name.startswith("Gift -"):
        return {
            "kind": "tool",
            "tool_type": "gift-package",
            "group": "tool",
        }
    if "bundle_of_all" in name:
        return {
            "kind": "tool",
            "tool_type": "bundle",
            "group": "tool",
        }
    if "swap_tool" in name:
        return {
            "kind": "tool",
            "tool_type": "swap-tool",
            "group": "tool",
        }

    if (
        prefab_tokens.intersection(CONTAINER_PREFABS)
        or "set supply crate series" in attributes
        or "StickerCapsule" in tags
        or str(resolved.get("inv_container_and_tools", "")).endswith(("_case", "_capsule", "_box"))
        or tool.get("type") == "supply_crate"
    ):
        return {
            "kind": "container",
            "group": "container",
        }

    if tool or resolved.get("inv_container_and_tools") == "tool" or "recipe" in prefab_tokens:
        return {
            "kind": "tool",
            "tool_type": tool.get("type"),
            "group": "tool",
        }

    if any(token.startswith("customplayer") for token in prefab_tokens):
        side = None
        if isinstance(resolved.get("used_by_classes"), dict):
            classes = sorted(resolved["used_by_classes"].keys())
            if classes == ["counter-terrorists"]:
                side = "counter-terrorists"
            elif classes == ["terrorists"]:
                side = "terrorists"
        return {
            "kind": "agent",
            "group": "agent",
            "side": side,
        }

    if "hands_paintable" in prefab_tokens:
        return {
            "kind": "weapon",
            "group": "glove",
        }

    if "melee" in prefab_tokens or name.startswith("weapon_knife") or name == "weapon_bayonet":
        return {
            "kind": "weapon",
            "group": "knife",
        }

    if name.startswith("weapon_"):
        return {
            "kind": "weapon",
            "group": WEAPON_GROUPS.get(name, "other-weapon"),
        }

    if "commodity_pin" in prefab_tokens:
        return {
            "kind": "collectible",
            "group": "pin",
        }

    if "coin" in name.lower() or "trophy" in prefab_tokens or "pickem" in prefab_tokens:
        return {
            "kind": "collectible",
            "group": "collectible",
        }

    return {
        "kind": "other",
        "group": "other",
    }


def classify_sticker_finish(codename: str) -> str:
    lowered = codename.lower()
    for token, label in STICKER_FINISH_ORDER:
        if token in lowered:
            return label
    return "Paper"


def is_graffiti_kit(raw_kit: dict[str, Any]) -> bool:
    codename = str(raw_kit.get("name", "")).lower()
    material = str(raw_kit.get("sticker_material", "")).lower()
    return codename.endswith("_graffiti") or material.endswith("_graffiti")


def classify_sticker_kit(raw_kit: dict[str, Any]) -> dict[str, Any]:
    codename = str(raw_kit.get("name", ""))
    if raw_kit.get("patch_material"):
        kind = "patch"
    elif is_graffiti_kit(raw_kit):
        kind = "graffiti"
    else:
        kind = "sticker"
    association = "none"
    if raw_kit.get("tournament_player_id"):
        association = "player"
    elif raw_kit.get("tournament_team_id"):
        association = "team"
    elif raw_kit.get("tournament_event_id"):
        association = "tournament"
    return {
        "kind": kind,
        "finish": classify_sticker_finish(codename),
        "association": association,
    }


def supported_exteriors(min_float: float | None, max_float: float | None) -> list[dict[str, Any]]:
    if min_float is None or max_float is None:
        return []
    if max_float <= min_float and max_float == 0:
        return [
            {
                "id": "vanilla",
                "name": "Vanilla",
                "short_name": "Vanilla",
                "min_float": 0.0,
                "max_float": 0.0,
            }
        ]
    output = []
    for exterior in STANDARD_EXTERIORS:
        if min_float < exterior["max_float"] and max_float > exterior["min_float"]:
            output.append(exterior)
    return output


def parse_leaf_entry(entry: str) -> dict[str, str] | None:
    match = LEAF_ENTRY_RE.match(entry)
    if not match:
        return None
    return {
        "token": match.group("token"),
        "target": match.group("target"),
    }


def flatten_loot_list(
    root_name: str,
    loot_lists: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []

    def walk(name: str, path: list[str], flags: set[str]) -> None:
        node = loot_lists.get(name)
        if not isinstance(node, dict):
            return
        local_flags = set(flags)
        if node.get("will_produce_stattrak") == "1":
            local_flags.add("will_produce_stattrak")

        for key, weight in node.items():
            if key == "will_produce_stattrak":
                continue
            if key in loot_lists:
                walk(key, path + [key], local_flags)
                continue
            flattened.append(
                {
                    "entry": key,
                    "weight": weight,
                    "path": path + [name],
                    "flags": sorted(local_flags),
                    "tier": infer_loot_tier(path + [name]),
                }
            )

    walk(root_name, [], set())
    return flattened


def resolve_loot_list_root(
    candidates: list[str],
    loot_lists: dict[str, dict[str, Any]],
) -> tuple[str | None, list[dict[str, Any]]]:
    for candidate in candidates:
        if candidate in loot_lists:
            return candidate, flatten_loot_list(candidate, loot_lists)

    for candidate in candidates:
        tier_lists = [f"{candidate}_{tier}" for tier in AGGREGATE_LOOT_TIERS if f"{candidate}_{tier}" in loot_lists]
        if not tier_lists:
            continue
        flattened: list[dict[str, Any]] = []
        for tier_list in tier_lists:
            flattened.extend(flatten_loot_list(tier_list, loot_lists))
        return candidate, unique_list(flattened)

    return None, []


def infer_loot_tier(path: list[str]) -> str | None:
    for node in reversed(path):
        for tier in ("ancient", "legendary", "mythical", "rare", "uncommon"):
            if node.endswith(f"_{tier}"):
                return tier
    return None


def resolve_container_loot_list_candidates(item_record: dict[str, Any], revolving_loot_lists: dict[str, str]) -> list[str]:
    raw = item_record["resolved"]
    tags = raw.get("tags") if isinstance(raw.get("tags"), dict) else {}
    name = str(raw.get("name", ""))
    candidates = [name]

    loot_list_name = raw.get("loot_list_name")
    if loot_list_name:
        candidates.append(str(loot_list_name))
        if not str(loot_list_name).endswith("_lootlist"):
            candidates.append(f"{loot_list_name}_lootlist")

    if name.startswith("selfopeningitem_"):
        candidates.append(name.replace("selfopeningitem_", "", 1))
    if name and not name.endswith("_lootlist"):
        candidates.append(f"{name}_lootlist")

    signature_match = SIGNATURE_PACK_RE.match(name)
    if signature_match:
        candidates.append(
            f"{signature_match.group('event')}_signatures_{signature_match.group('suffix')}"
        )

    item_set_tag = tags.get("ItemSet") if isinstance(tags.get("ItemSet"), dict) else {}
    if item_set_tag.get("tag_value"):
        candidates.append(item_set_tag["tag_value"])

    sticker_capsule_tag = tags.get("StickerCapsule") if isinstance(tags.get("StickerCapsule"), dict) else {}
    if sticker_capsule_tag.get("tag_value"):
        raw_tag = sticker_capsule_tag["tag_value"]
        candidates.append(raw_tag)
        if raw_tag.endswith("_collection"):
            candidates.append(raw_tag[: -len("_collection")] + "_lootlist")
        if not raw_tag.endswith("_lootlist"):
            candidates.append(raw_tag + "_lootlist")

    spray_capsule_tag = tags.get("SprayCapsule") if isinstance(tags.get("SprayCapsule"), dict) else {}
    if spray_capsule_tag.get("tag_value"):
        raw_tag = spray_capsule_tag["tag_value"]
        candidates.append(raw_tag)
        if not raw_tag.endswith("_lootlist"):
            candidates.append(raw_tag + "_lootlist")

    if name.startswith("crate_musickit_"):
        candidates.append(name + "_lootlist")

    series_id = extract_supply_crate_series(raw)
    if series_id is not None:
        revolving_loot_list = revolving_loot_lists.get(str(series_id))
        if revolving_loot_list:
            candidates.append(revolving_loot_list)

    return list(dict.fromkeys(candidate for candidate in candidates if candidate))


def build_core_dataset(items_game: dict[str, Any], localizer: Localizer) -> dict[str, Any]:
    prefabs_raw = items_game.get("prefabs", {})
    prefabs_resolved, prefab_chains = resolve_prefabs(prefabs_raw)
    resolved_items, prefab_usage = resolve_item_definitions(items_game.get("items", {}), prefabs_resolved, prefab_chains)

    items_by_name = {
        record["name"]: record
        for record in resolved_items.values()
        if record.get("name")
    }

    paint_kits = {}
    paint_kits_by_name = {}
    for paint_kit_id, raw_paint_kit in items_game.get("paint_kits", {}).items():
        rarity_ref = items_game.get("paint_kits_rarity", {}).get(paint_kit_id)
        record = {
            "id": parse_int(paint_kit_id),
            "game_id": parse_int(paint_kit_id),
            "name": raw_paint_kit.get("name"),
            "display_name_token": raw_paint_kit.get("description_tag"),
            "display_name": localizer.resolve(raw_paint_kit.get("description_tag")),
            "wear_min": parse_float(raw_paint_kit.get("wear_remap_min")),
            "wear_max": parse_float(raw_paint_kit.get("wear_remap_max")),
            "style_code": parse_int(raw_paint_kit.get("style")),
            "pattern": raw_paint_kit.get("pattern"),
            "rarity_ref": rarity_ref,
            "resolved": raw_paint_kit,
        }
        paint_kits[paint_kit_id] = record
        if record["name"]:
            paint_kits_by_name[record["name"]] = record

    sticker_kits = {}
    sticker_kits_by_name = {}
    for sticker_kit_id, raw_sticker_kit in items_game.get("sticker_kits", {}).items():
        record = {
            "id": parse_int(sticker_kit_id),
            "game_id": parse_int(sticker_kit_id),
            "name": raw_sticker_kit.get("name"),
            "display_name_token": raw_sticker_kit.get("item_name"),
            "display_name": localizer.resolve(raw_sticker_kit.get("item_name")),
            "description_token": raw_sticker_kit.get("description_string"),
            "description": localizer.resolve(raw_sticker_kit.get("description_string")),
            "classification": classify_sticker_kit(raw_sticker_kit),
            "resolved": raw_sticker_kit,
        }
        sticker_kits[sticker_kit_id] = record
        if record["name"]:
            sticker_kits_by_name[record["name"]] = record

    keychains = {}
    keychains_by_name = {}
    for keychain_id, raw_keychain in items_game.get("keychain_definitions", {}).items():
        record = {
            "id": parse_int(keychain_id),
            "game_id": parse_int(keychain_id),
            "name": raw_keychain.get("name"),
            "display_name_token": raw_keychain.get("loc_name"),
            "display_name": localizer.resolve(raw_keychain.get("loc_name")),
            "description_token": raw_keychain.get("loc_description"),
            "description": localizer.resolve(raw_keychain.get("loc_description")),
            "resolved": raw_keychain,
        }
        keychains[keychain_id] = record
        if record["name"]:
            keychains_by_name[record["name"]] = record

    music_definitions = {}
    music_by_name = {}
    for music_id, raw_music in items_game.get("music_definitions", {}).items():
        record = {
            "id": parse_int(music_id),
            "game_id": parse_int(music_id),
            "name": raw_music.get("name"),
            "display_name_token": raw_music.get("loc_name"),
            "display_name": localizer.resolve(raw_music.get("loc_name")),
            "description_token": raw_music.get("loc_description"),
            "description": localizer.resolve(raw_music.get("loc_description")),
            "resolved": raw_music,
        }
        music_definitions[music_id] = record
        if record["name"]:
            music_by_name[record["name"]] = record

    item_sets = {}
    for item_set_id, raw_item_set in items_game.get("item_sets", {}).items():
        parsed_items = []
        for entry in (raw_item_set.get("items") or {}).keys():
            parsed = parse_leaf_entry(entry)
            if not parsed:
                continue
            parsed_items.append(
                {
                    "entry": entry,
                    "token": parsed["token"],
                    "target": parsed["target"],
                }
            )
        item_sets[item_set_id] = {
            "id": item_set_id,
            "game_id": item_set_id,
            "display_name_token": raw_item_set.get("name"),
            "display_name": localizer.resolve(raw_item_set.get("name")),
            "description_token": raw_item_set.get("set_description"),
            "description": localizer.resolve(raw_item_set.get("set_description")),
            "items": parsed_items,
            "resolved": raw_item_set,
        }

    loot_lists = {}
    for source_block in ("client_loot_lists", "quest_reward_loot_lists"):
        for loot_list_id, raw_loot_list in items_game.get(source_block, {}).items():
            loot_lists[loot_list_id] = {
                "id": loot_list_id,
                "game_id": loot_list_id,
                "source_block": source_block,
                "resolved": raw_loot_list,
            }

    revolving_loot_lists = {
        str(series_id): str(loot_list_name)
        for series_id, loot_list_name in items_game.get("revolving_loot_lists", {}).items()
    }

    enums = {
        "rarities": items_game.get("rarities", {}),
        "qualities": items_game.get("qualities", {}),
        "colors": items_game.get("colors", {}),
        "graffiti_tints": items_game.get("graffiti_tints", {}),
        "exteriors": {entry["id"]: entry for entry in STANDARD_EXTERIORS},
    }

    handled_blocks = set(items_game.keys())
    unknown_blocks = sorted(handled_blocks.difference(HANDLED_TOP_LEVEL_BLOCKS))

    return {
        "items_by_name": items_by_name,
        "paint_kits_by_name": paint_kits_by_name,
        "sticker_kits_by_name": sticker_kits_by_name,
        "music_by_name": music_by_name,
        "resolved_items": resolved_items,
        "prefabs": {
            name: {
                "id": name,
                "name": name,
                "prefab_chain": prefab_chains.get(name, []),
                "resolved": resolved,
            }
            for name, resolved in prefabs_resolved.items()
        },
        "paint_kits": paint_kits,
        "sticker_kits": sticker_kits,
        "item_sets": item_sets,
        "loot_lists": loot_lists,
        "revolving_loot_lists": revolving_loot_lists,
        "keychains": keychains,
        "music_definitions": music_definitions,
        "locales": items_game,
        "enums": enums,
        "raw": {
            "pro_event_results": items_game.get("pro_event_results", {}),
            "pro_players": items_game.get("pro_players", {}),
            "pro_teams": items_game.get("pro_teams", {}),
        },
        "reports": {
            "unknown_blocks": unknown_blocks,
            "unknown_prefabs": summarize_unknown_prefabs(resolved_items, prefab_usage),
        },
    }


def summarize_unknown_prefabs(
    resolved_items: dict[str, dict[str, Any]],
    prefab_usage: Counter[str],
) -> list[dict[str, Any]]:
    unknown: Counter[str] = Counter()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item_id, record in resolved_items.items():
        if record["classification"]["kind"] != "other":
            continue
        prefab_spec = record.get("prefab_spec") or "<none>"
        unknown[prefab_spec] += 1
        if len(examples[prefab_spec]) < 5:
            examples[prefab_spec].append(
                {
                    "id": record["id"],
                    "name": record["name"],
                }
            )
    return [
        {
            "prefab_spec": prefab_spec,
            "count": count,
            "examples": examples[prefab_spec],
        }
        for prefab_spec, count in unknown.most_common()
    ]


def derive_api_dataset(core: dict[str, Any], localizer: Localizer) -> dict[str, Any]:
    items_by_name = core["items_by_name"]
    paint_kits_by_name = core["paint_kits_by_name"]
    sticker_kits_by_name = core["sticker_kits_by_name"]
    music_by_name = core["music_by_name"]
    resolved_items = core["resolved_items"]
    item_sets = core["item_sets"]
    loot_lists = {key: value["resolved"] for key, value in core["loot_lists"].items()}
    revolving_loot_lists = core["revolving_loot_lists"]

    finishes = build_finish_entities(core["paint_kits"])
    weapons = build_weapon_entities(resolved_items, localizer)
    collections = build_collection_entities(item_sets, items_by_name, paint_kits_by_name, localizer)
    containers, unresolved_containers = build_container_entities(
        resolved_items,
        loot_lists,
        revolving_loot_lists,
        item_sets,
        items_by_name,
        paint_kits_by_name,
        sticker_kits_by_name,
        music_by_name,
        localizer,
    )
    skins, skin_variants, skin_relations = build_skin_entities(
        collections,
        containers,
        items_by_name,
        paint_kits_by_name,
        weapons,
        localizer,
    )
    stickers = build_sticker_entities(core["sticker_kits"], core["raw"], localizer)
    patches = build_patch_entities(core["sticker_kits"], core["raw"], localizer)
    graffiti = build_graffiti_entities(core["sticker_kits"], core["raw"], localizer)
    special_drops = build_special_drop_entities(containers)
    players = build_player_entities(core["raw"]["pro_players"], stickers)
    teams = build_team_entities(core["raw"]["pro_teams"], core["raw"]["pro_players"], stickers, patches, graffiti, localizer)
    tournaments = build_tournament_entities(
        core["raw"]["pro_event_results"],
        containers,
        stickers,
        patches,
        graffiti,
        teams,
        players,
        localizer,
    )
    sticker_capsules = {
        container_id: container
        for container_id, container in containers.items()
        if container["container_kind"] == "sticker-capsule"
    }
    agents = build_agents(resolved_items, localizer)
    charms = build_charm_entities(core["keychains"])
    music_kits = build_music_entities(core["music_definitions"], containers)
    tools = build_tool_entities(resolved_items, localizer)
    assets = build_asset_entities(core, weapons, containers, agents, tools, charms, music_kits, stickers, patches, graffiti)

    relations = build_relations(
        skins,
        skin_variants,
        collections,
        containers,
        stickers,
        patches,
        graffiti,
        tournaments,
        teams,
        players,
        skin_relations,
    )
    indexes = build_indexes(
        finishes=finishes,
        skins=skins,
        skin_variants=skin_variants,
        collections=collections,
        containers=containers,
        stickers=stickers,
        patches=patches,
        graffiti=graffiti,
        special_drops=special_drops,
        tournaments=tournaments,
        teams=teams,
        players=players,
        agents=agents,
        charms=charms,
        music_kits=music_kits,
        weapons=weapons,
    )

    return {
        "finishes": finishes,
        "weapons": weapons,
        "collections": collections,
        "containers": containers,
        "skins": skins,
        "skin_variants": skin_variants,
        "stickers": stickers,
        "patches": patches,
        "graffiti": graffiti,
        "special_drops": special_drops,
        "tournaments": tournaments,
        "teams": teams,
        "players": players,
        "sticker_capsules": sticker_capsules,
        "agents": agents,
        "charms": charms,
        "music_kits": music_kits,
        "tools": tools,
        "assets": assets,
        "relations": relations,
        "indexes": indexes,
        "reports": {
            "unresolved_containers": unresolved_containers,
            "skin_relations": skin_relations,
        },
    }


def build_weapon_entities(
    resolved_items: dict[str, dict[str, Any]],
    localizer: Localizer,
) -> dict[str, dict[str, Any]]:
    weapons = {}
    for item_id, record in resolved_items.items():
        classification = record["classification"]
        if classification["kind"] != "weapon":
            continue
        resolved = record["resolved"]
        weapons[item_id] = {
            "id": record["id"],
            "game_id": record["game_id"],
            "codename": record["name"],
            "name_token": resolved.get("item_name"),
            "name": localizer.resolve(resolved.get("item_name")) or record["name"],
            "description_token": resolved.get("item_description"),
            "description": localizer.resolve(resolved.get("item_description")),
            "type_token": resolved.get("item_type_name"),
            "type_name": localizer.resolve(resolved.get("item_type_name")),
            "weapon_group": classification["group"],
            "side": classification.get("side"),
            "prefab_chain": record["prefab_chain"],
            "search_slug": slugify(localizer.resolve(resolved.get("item_name")) or record["name"] or item_id),
            "resolved": resolved,
        }
    return weapons


def build_finish_entities(paint_kits: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    finishes = {}
    for paint_kit_id, record in paint_kits.items():
        finishes[paint_kit_id] = {
            "id": record["id"],
            "game_id": record["game_id"],
            "codename": record["name"],
            "name_token": record["display_name_token"],
            "name": record["display_name"] or record["name"],
            "wear": {
                "min_float": record["wear_min"],
                "max_float": record["wear_max"],
            },
            "style_code": record["style_code"],
            "pattern": record["pattern"],
            "rarity_ref": record["rarity_ref"],
            "search_slug": slugify(record["display_name"] or record["name"] or paint_kit_id),
            "resolved": record["resolved"],
        }
    return finishes


def build_collection_entities(
    item_sets: dict[str, dict[str, Any]],
    items_by_name: dict[str, dict[str, Any]],
    paint_kits_by_name: dict[str, dict[str, Any]],
    localizer: Localizer,
) -> dict[str, dict[str, Any]]:
    collections = {}
    for collection_id, record in item_sets.items():
        skin_refs = []
        for item in record["items"]:
            weapon = items_by_name.get(item["target"])
            paint_kit = paint_kits_by_name.get(item["token"])
            if not weapon or not paint_kit:
                continue
            skin_id = f"{weapon['id']}-{paint_kit['id']}"
            skin_refs.append(
                {
                    "skin_id": skin_id,
                    "weapon_id": weapon["id"],
                    "paint_kit_id": paint_kit["id"],
                }
            )
        collections[collection_id] = {
            "id": collection_id,
            "game_id": collection_id,
            "name_token": record["display_name_token"],
            "name": record["display_name"] or collection_id,
            "description_token": record["description_token"],
            "description": record["description"],
            "kind": "item-set",
            "skin_refs": skin_refs,
            "search_slug": slugify(record["display_name"] or collection_id),
        }
    return collections


def build_container_entities(
    resolved_items: dict[str, dict[str, Any]],
    loot_lists: dict[str, dict[str, Any]],
    revolving_loot_lists: dict[str, str],
    item_sets: dict[str, dict[str, Any]],
    items_by_name: dict[str, dict[str, Any]],
    paint_kits_by_name: dict[str, dict[str, Any]],
    sticker_kits_by_name: dict[str, dict[str, Any]],
    music_by_name: dict[str, dict[str, Any]],
    localizer: Localizer,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    containers = {}
    unresolved = []
    for item_id, record in resolved_items.items():
        if record["classification"]["kind"] != "container":
            continue
        resolved = record["resolved"]
        candidates = resolve_container_loot_list_candidates(record, revolving_loot_lists)
        root_loot_list, flattened = resolve_loot_list_root(candidates, loot_lists)
        contents, unresolved_entries = resolve_container_contents(
            flattened,
            items_by_name,
            paint_kits_by_name,
            sticker_kits_by_name,
            music_by_name,
        )
        contents_source = {"type": "loot-list", "id": root_loot_list} if root_loot_list else None
        if root_loot_list is None:
            fallback_item_set, fallback_contents = resolve_container_item_set_fallback(
                candidates,
                item_sets,
                items_by_name,
                paint_kits_by_name,
            )
            if fallback_contents:
                contents = fallback_contents
                contents_source = {"type": "item-set", "id": fallback_item_set}

        container_kind = determine_container_kind(resolved)
        container = {
            "id": record["id"],
            "game_id": record["game_id"],
            "codename": record["name"],
            "name_token": resolved.get("item_name"),
            "name": localizer.resolve(resolved.get("item_name")) or record["name"],
            "description_token": resolved.get("item_description"),
            "description": localizer.resolve(resolved.get("item_description")),
            "container_kind": container_kind,
            "series_id": extract_supply_crate_series(resolved),
            "tournament_event_id": extract_tournament_event_id(resolved),
            "root_loot_list": root_loot_list,
            "contents_source": contents_source,
            "rare_special_item": {
                "name_token": resolved.get("loot_list_rare_item_name"),
                "name": localizer.resolve(resolved.get("loot_list_rare_item_name")),
                "footer_token": resolved.get("loot_list_rare_item_footer"),
                "footer": localizer.resolve(resolved.get("loot_list_rare_item_footer")),
            },
            "loot_list_candidates": candidates,
            "contents": contents,
            "search_slug": slugify(localizer.resolve(resolved.get("item_name")) or record["name"] or item_id),
        }
        containers[item_id] = container

        if contents_source is None or unresolved_entries:
            unresolved.append(
                {
                    "container_id": record["id"],
                    "codename": record["name"],
                    "root_loot_list": root_loot_list,
                    "loot_list_candidates": candidates,
                    "unresolved_entries": unresolved_entries,
                }
            )
    return containers, unresolved


def resolve_container_item_set_fallback(
    candidates: list[str],
    item_sets: dict[str, dict[str, Any]],
    items_by_name: dict[str, dict[str, Any]],
    paint_kits_by_name: dict[str, dict[str, Any]],
) -> tuple[str | None, list[dict[str, Any]]]:
    for candidate in candidates:
        item_set = item_sets.get(candidate)
        if not item_set:
            continue
        contents = []
        for item in item_set["items"]:
            weapon = items_by_name.get(item["target"])
            paint_kit = paint_kits_by_name.get(item["token"])
            if not weapon or not paint_kit:
                continue
            contents.append(
                {
                    "kind": "skin",
                    "skin_id": f"{weapon['id']}-{paint_kit['id']}",
                    "weapon_id": weapon["id"],
                    "paint_kit_id": paint_kit["id"],
                    "tier": None,
                    "flags": ["item_set_fallback"],
                }
            )
        if contents:
            return candidate, unique_list(contents)
    return None, []


def extract_supply_crate_series(resolved: dict[str, Any]) -> int | None:
    attributes = resolved.get("attributes") if isinstance(resolved.get("attributes"), dict) else {}
    entry = attributes.get("set supply crate series")
    if isinstance(entry, dict):
        return parse_int(entry.get("value"))
    return parse_int(entry)


def extract_tournament_event_id(resolved: dict[str, Any]) -> int | None:
    attributes = resolved.get("attributes") if isinstance(resolved.get("attributes"), dict) else {}
    entry = attributes.get("tournament event id")
    if isinstance(entry, dict):
        return parse_int(entry.get("value"))
    if entry is not None:
        return parse_int(entry)
    return parse_int(resolved.get("tournament_event_id"))


def determine_container_kind(resolved: dict[str, Any]) -> str:
    name = str(resolved.get("name", ""))
    prefab = str(resolved.get("prefab", ""))
    tags = resolved.get("tags") if isinstance(resolved.get("tags"), dict) else {}
    if prefab == "weapon_case_souvenirpkg":
        return "souvenir-package"
    if "StickerCapsule" in tags or "sticker_pack" in name or "signature_pack" in name:
        return "sticker-capsule"
    if "musickit" in name:
        return "music-kit-box"
    if "pins" in name:
        return "pin-capsule"
    if "graffiti" in name:
        return "graffiti-box"
    if prefab == "weapon_case":
        return "weapon-case"
    return "container"


def is_special_drop_entry(entry: str) -> bool:
    return (
        entry == "unusual_revolving_list"
        or entry == "all_entries_as_additional_drops"
        or entry == "match_highlight_reel_keychain"
        or entry.endswith("_unusual")
    )


def infer_special_drop_kind(entry: str) -> str:
    if entry == "all_entries_as_additional_drops":
        return "additional-drops-rule"
    if entry == "match_highlight_reel_keychain":
        return "souvenir-keychain-bonus"
    if entry == "unusual_revolving_list" or entry.endswith("_unusual"):
        return "rare-special-item-pool"
    return "special-drop"


def resolve_container_contents(
    flattened_entries: list[dict[str, Any]],
    items_by_name: dict[str, dict[str, Any]],
    paint_kits_by_name: dict[str, dict[str, Any]],
    sticker_kits_by_name: dict[str, dict[str, Any]],
    music_by_name: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    contents = []
    unresolved = []
    for entry in flattened_entries:
        if entry["entry"] in IGNORED_LOOT_ENTRIES:
            continue
        parsed = parse_leaf_entry(entry["entry"])
        if parsed:
            target = parsed["target"]
            token = parsed["token"]
            if target.startswith("weapon_"):
                weapon = items_by_name.get(target)
                paint_kit = paint_kits_by_name.get(token)
                if weapon and paint_kit:
                    contents.append(
                        {
                            "kind": "skin",
                            "skin_id": f"{weapon['id']}-{paint_kit['id']}",
                            "weapon_id": weapon["id"],
                            "paint_kit_id": paint_kit["id"],
                            "tier": entry["tier"],
                            "flags": entry["flags"],
                        }
                    )
                    continue
            if target in {"sticker", "patch"}:
                sticker = sticker_kits_by_name.get(token)
                if sticker:
                    contents.append(
                        {
                            "kind": sticker["classification"]["kind"],
                            "sticker_id": sticker["id"],
                            "tier": entry["tier"],
                            "flags": entry["flags"],
                        }
                    )
                    continue
            if target == "spray":
                graffiti = sticker_kits_by_name.get(token)
                if graffiti:
                    contents.append(
                        {
                            "kind": "graffiti",
                            "graffiti_id": graffiti["id"],
                            "tier": entry["tier"],
                            "flags": entry["flags"],
                        }
                    )
                    continue
            if target == "musickit":
                music = music_by_name.get(token)
                if music:
                    contents.append(
                        {
                            "kind": "music-kit",
                            "music_kit_id": music["id"],
                            "tier": entry["tier"],
                            "flags": entry["flags"],
                        }
                    )
                    continue
        if is_special_drop_entry(entry["entry"]):
            contents.append(
                {
                    "kind": "special-drop",
                    "special_drop_id": entry["entry"],
                    "special_drop_kind": infer_special_drop_kind(entry["entry"]),
                    "tier": entry["tier"],
                    "flags": entry["flags"],
                    "weight": entry.get("weight"),
                }
            )
            continue
        direct_item = items_by_name.get(entry["entry"])
        if direct_item:
            contents.append(
                {
                    "kind": direct_item["classification"]["kind"],
                    "item_definition_id": direct_item["id"],
                    "tier": entry["tier"],
                    "flags": entry["flags"],
                }
            )
            continue
        unresolved.append(entry)
    return unique_list(contents), unresolved


def build_skin_entities(
    collections: dict[str, dict[str, Any]],
    containers: dict[str, dict[str, Any]],
    items_by_name: dict[str, dict[str, Any]],
    paint_kits_by_name: dict[str, dict[str, Any]],
    weapons: dict[str, dict[str, Any]],
    localizer: Localizer,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    skins: dict[str, dict[str, Any]] = {}
    skin_relations: dict[str, Any] = {
        "skin_to_sources": defaultdict(lambda: {"collections": [], "containers": []}),
        "collection_to_skins": defaultdict(list),
        "container_to_skins": defaultdict(list),
    }
    paint_kits_by_id = {record["id"]: record for record in paint_kits_by_name.values()}

    for collection_id, collection in collections.items():
        for skin_ref in collection["skin_refs"]:
            skin_id = skin_ref["skin_id"]
            add_skin_source(
                skins,
                skin_id,
                skin_ref["weapon_id"],
                skin_ref["paint_kit_id"],
                weapons,
                paint_kits_by_id,
                items_by_name,
                collection_source={"id": collection_id, "name": collection["name"]},
                container_source=None,
                localizer=localizer,
            )
            skin_relations["skin_to_sources"][skin_id]["collections"].append(collection_id)
            skin_relations["collection_to_skins"][collection_id].append(skin_id)

    for container_id, container in containers.items():
        for content in container["contents"]:
            if content["kind"] != "skin":
                continue
            skin_id = content["skin_id"]
            add_skin_source(
                skins,
                skin_id,
                content["weapon_id"],
                content["paint_kit_id"],
                weapons,
                paint_kits_by_id,
                items_by_name,
                collection_source=None,
                container_source={
                    "id": container_id,
                    "name": container["name"],
                    "kind": container["container_kind"],
                    "tier": content.get("tier"),
                    "flags": content.get("flags", []),
                },
                localizer=localizer,
            )
            skin_relations["skin_to_sources"][skin_id]["containers"].append(container_id)
            skin_relations["container_to_skins"][container_id].append(skin_id)

    variants = {}
    for skin_id, skin in skins.items():
        variant_ids = []
        exteriors = skin["supported_exteriors"]
        if not exteriors:
            exteriors = [{"id": "vanilla", "name": "Vanilla", "short_name": "Vanilla"}]
        qualities = []
        if skin["availability"]["normal"]:
            qualities.append(("normal", "Normal"))
        if skin["availability"]["stattrak"]:
            qualities.append(("stattrak", "StatTrak"))
        if skin["availability"]["souvenir"]:
            qualities.append(("souvenir", "Souvenir"))
        for quality_id, quality_name in qualities:
            for exterior in exteriors:
                variant_id = f"{skin_id}__{quality_id}__{exterior['id']}"
                market_name = build_market_name(
                    weapon_name=skin["weapon"]["name"],
                    skin_name=skin["finish"]["name"],
                    quality=quality_name,
                    exterior_name=exterior["name"],
                )
                variants[variant_id] = {
                    "id": variant_id,
                    "skin_id": skin_id,
                    "quality": quality_id,
                    "quality_name": quality_name,
                    "exterior": exterior["id"],
                    "exterior_name": exterior["name"],
                    "market_hash_name": market_name,
                    "search_slug": slugify(market_name),
                }
                variant_ids.append(variant_id)
        skin["variant_ids"] = variant_ids

    skin_relations["skin_to_sources"] = {
        key: {
            "collections": sorted(set(value["collections"])),
            "containers": sorted(set(value["containers"])),
        }
        for key, value in skin_relations["skin_to_sources"].items()
    }
    skin_relations["collection_to_skins"] = {
        key: sorted(set(value))
        for key, value in skin_relations["collection_to_skins"].items()
    }
    skin_relations["container_to_skins"] = {
        key: sorted(set(value))
        for key, value in skin_relations["container_to_skins"].items()
    }

    return skins, variants, skin_relations


def add_skin_source(
    skins: dict[str, dict[str, Any]],
    skin_id: str,
    weapon_id: int,
    paint_kit_id: int,
    weapons: dict[str, dict[str, Any]],
    paint_kits: dict[Any, dict[str, Any]],
    items_by_name: dict[str, dict[str, Any]],
    collection_source: dict[str, Any] | None,
    container_source: dict[str, Any] | None,
    localizer: Localizer,
) -> None:
    weapon = weapons.get(str(weapon_id))
    if weapon is None:
        weapon = weapons.get(weapon_id)
    if weapon is None:
        return
    paint_kit = paint_kits.get(paint_kit_id) or paint_kits.get(str(paint_kit_id))
    if paint_kit is None:
        return
    if skin_id not in skins:
        wear_min = paint_kit.get("wear_min")
        wear_max = paint_kit.get("wear_max")
        exteriors = supported_exteriors(wear_min, wear_max)
        skins[skin_id] = {
            "id": skin_id,
            "game_ref": {
                "weapon_id": weapon_id,
                "paint_kit_id": paint_kit_id,
            },
            "weapon": {
                "id": weapon_id,
                "codename": weapon["codename"],
                "name": weapon["name"],
                "weapon_group": weapon["weapon_group"],
            },
            "finish": {
                "id": paint_kit_id,
                "codename": paint_kit["name"],
                "name": paint_kit["display_name"] or paint_kit["name"],
                "style_code": paint_kit["style_code"],
                "rarity_ref": paint_kit["rarity_ref"],
            },
            "name": f"{weapon['name']} | {paint_kit['display_name'] or paint_kit['name']}",
            "wear": {
                "min_float": wear_min,
                "max_float": wear_max,
            },
            "supported_exteriors": exteriors,
            "availability": {
                "normal": False,
                "stattrak": False,
                "souvenir": False,
            },
            "sources": {
                "collections": [],
                "containers": [],
            },
            "search_slug": slugify(f"{weapon['name']} {paint_kit['display_name'] or paint_kit['name']}"),
        }
    if collection_source is not None:
        skins[skin_id]["availability"]["normal"] = True
        skins[skin_id]["sources"]["collections"].append(collection_source)
    if container_source is not None:
        container_kind = container_source["kind"]
        if container_kind == "souvenir-package":
            skins[skin_id]["availability"]["souvenir"] = weapon["weapon_group"] not in {"knife", "glove"}
        elif container_kind == "weapon-case":
            skins[skin_id]["availability"]["normal"] = True
            skins[skin_id]["availability"]["stattrak"] = weapon["weapon_group"] not in {"glove"}
        else:
            skins[skin_id]["availability"]["normal"] = True
        skins[skin_id]["sources"]["containers"].append(container_source)
    skins[skin_id]["sources"]["collections"] = unique_list(skins[skin_id]["sources"]["collections"])
    skins[skin_id]["sources"]["containers"] = unique_list(skins[skin_id]["sources"]["containers"])


def build_market_name(weapon_name: str, skin_name: str, quality: str, exterior_name: str) -> str:
    base_name = f"{weapon_name} | {skin_name}"
    if exterior_name == "Vanilla":
        suffix = ""
    else:
        suffix = f" ({exterior_name})"
    if quality == "StatTrak":
        return f"StatTrak™ {base_name}{suffix}"
    if quality == "Souvenir":
        return f"Souvenir {base_name}{suffix}"
    return f"{base_name}{suffix}"


def build_sticker_entities(
    sticker_kits: dict[str, dict[str, Any]],
    raw_blocks: dict[str, Any],
    localizer: Localizer,
) -> dict[str, dict[str, Any]]:
    return build_decal_entities(sticker_kits, raw_blocks, allowed_kind="sticker")


def build_patch_entities(
    sticker_kits: dict[str, dict[str, Any]],
    raw_blocks: dict[str, Any],
    localizer: Localizer,
) -> dict[str, dict[str, Any]]:
    return build_decal_entities(sticker_kits, raw_blocks, allowed_kind="patch")


def build_graffiti_entities(
    sticker_kits: dict[str, dict[str, Any]],
    raw_blocks: dict[str, Any],
    localizer: Localizer,
) -> dict[str, dict[str, Any]]:
    return build_decal_entities(sticker_kits, raw_blocks, allowed_kind="graffiti")


def build_decal_entities(
    sticker_kits: dict[str, dict[str, Any]],
    raw_blocks: dict[str, Any],
    allowed_kind: str,
) -> dict[str, dict[str, Any]]:
    pro_players = raw_blocks.get("pro_players", {})
    pro_teams = raw_blocks.get("pro_teams", {})
    decals = {}
    for sticker_id, record in sticker_kits.items():
        if record["classification"]["kind"] != allowed_kind:
            continue
        resolved = record["resolved"]
        player_id = resolved.get("tournament_player_id")
        team_id = resolved.get("tournament_team_id")
        decals[sticker_id] = {
            "id": record["id"],
            "game_id": record["game_id"],
            "codename": record["name"],
            "name": record["display_name"] or record["name"],
            "description": record["description"],
            "kind": record["classification"]["kind"],
            "finish": record["classification"]["finish"],
            "association": record["classification"]["association"],
            "rarity_ref": resolved.get("item_rarity"),
            "tournament_event_id": parse_int(resolved.get("tournament_event_id")),
            "team_id": parse_int(team_id),
            "player_id": parse_int(player_id),
            "team_name": resolve_pro_name(pro_teams.get(str(team_id))),
            "player_name": resolve_pro_name(pro_players.get(str(player_id))),
            "material": resolved.get("patch_material") or resolved.get("sticker_material"),
            "search_slug": slugify(record["display_name"] or record["name"] or sticker_id),
        }
    return decals


def build_special_drop_entities(containers: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    entities: dict[str, dict[str, Any]] = {}
    for container_id, container in containers.items():
        for content in container["contents"]:
            if content["kind"] != "special-drop":
                continue
            special_drop_id = content["special_drop_id"]
            entity = entities.setdefault(
                special_drop_id,
                {
                    "id": special_drop_id,
                    "kind": content["special_drop_kind"],
                    "name": special_drop_name(special_drop_id),
                    "raw_token": special_drop_id,
                    "display_names": [],
                    "display_name_tokens": [],
                    "footers": [],
                    "footer_tokens": [],
                    "source_container_ids": [],
                    "search_slug": slugify(special_drop_name(special_drop_id)),
                },
            )
            entity["source_container_ids"].append(str(container_id))
            rare_special_item = container.get("rare_special_item") or {}
            if rare_special_item.get("name"):
                entity["display_names"].append(rare_special_item["name"])
            if rare_special_item.get("name_token"):
                entity["display_name_tokens"].append(rare_special_item["name_token"])
            if rare_special_item.get("footer"):
                entity["footers"].append(rare_special_item["footer"])
            if rare_special_item.get("footer_token"):
                entity["footer_tokens"].append(rare_special_item["footer_token"])
    for entity in entities.values():
        entity["source_container_ids"] = sorted(set(entity["source_container_ids"]))
        entity["display_names"] = sorted(set(entity["display_names"]))
        entity["display_name_tokens"] = sorted(set(entity["display_name_tokens"]))
        entity["footers"] = sorted(set(entity["footers"]))
        entity["footer_tokens"] = sorted(set(entity["footer_tokens"]))
        preferred_name = most_common_nonempty(entity["display_names"])
        if preferred_name:
            entity["name"] = preferred_name
    return entities


def special_drop_name(token: str) -> str:
    if token == "all_entries_as_additional_drops":
        return "All Entries As Additional Drops"
    if token == "match_highlight_reel_keychain":
        return "Match Highlight Reel Keychain Bonus"
    if token == "unusual_revolving_list":
        return "Unusual Revolving Special Item Pool"
    return token.replace("_", " ").title()


def resolve_pro_name(raw: Any) -> str | None:
    if not isinstance(raw, dict):
        return None
    for key in ("name", "tag", "code", "loc_name"):
        if raw.get(key):
            return str(raw[key])
    return None


def build_agents(resolved_items: dict[str, dict[str, Any]], localizer: Localizer) -> dict[str, dict[str, Any]]:
    agents = {}
    for item_id, record in resolved_items.items():
        if record["classification"]["kind"] != "agent":
            continue
        resolved = record["resolved"]
        agents[item_id] = {
            "id": record["id"],
            "game_id": record["game_id"],
            "codename": record["name"],
            "name": localizer.resolve(resolved.get("item_name")) or record["name"],
            "description": localizer.resolve(resolved.get("item_description")),
            "side": record["classification"].get("side"),
            "rarity_ref": resolved.get("item_rarity") or resolved.get("item_quality"),
            "search_slug": slugify(localizer.resolve(resolved.get("item_name")) or record["name"] or item_id),
        }
    return agents


def build_charm_entities(keychains: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    charms = {}
    for keychain_id, record in keychains.items():
        resolved = record["resolved"]
        charms[keychain_id] = {
            "id": record["id"],
            "game_id": record["game_id"],
            "codename": record["name"],
            "name": record["display_name"] or record["name"],
            "description": record["description"],
            "rarity_ref": resolved.get("item_rarity"),
            "search_slug": slugify(record["display_name"] or record["name"] or keychain_id),
        }
    return charms


def build_music_entities(
    music_definitions: dict[str, dict[str, Any]],
    containers: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    container_sources: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
    for container_id, container in containers.items():
        for content in container["contents"]:
            if content["kind"] != "music-kit":
                continue
            container_sources[content["music_kit_id"]].append(
                {
                    "container_id": container_id,
                    "container_name": container["name"],
                    "flags": content.get("flags", []),
                }
            )

    music_kits = {}
    for music_id, record in music_definitions.items():
        sources = container_sources.get(record["id"], [])
        music_kits[music_id] = {
            "id": record["id"],
            "game_id": record["game_id"],
            "codename": record["name"],
            "name": record["display_name"] or record["name"],
            "description": record["description"],
            "supports_stattrak": any("will_produce_stattrak" in source["flags"] for source in sources),
            "sources": unique_list(sources),
            "search_slug": slugify(record["display_name"] or record["name"] or music_id),
        }
    return music_kits


def build_tool_entities(
    resolved_items: dict[str, dict[str, Any]],
    localizer: Localizer,
) -> dict[str, dict[str, Any]]:
    tools = {}
    for item_id, record in resolved_items.items():
        if record["classification"]["kind"] != "tool":
            continue
        resolved = record["resolved"]
        tools[item_id] = {
            "id": record["id"],
            "game_id": record["game_id"],
            "codename": record["name"],
            "name": localizer.resolve(resolved.get("item_name")) or record["name"],
            "description": localizer.resolve(resolved.get("item_description")),
            "tool_type": record["classification"].get("tool_type"),
            "search_slug": slugify(localizer.resolve(resolved.get("item_name")) or record["name"] or item_id),
        }
    return tools


def build_player_entities(
    raw_players: dict[str, dict[str, Any]],
    stickers: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    player_stickers: defaultdict[str, list[str]] = defaultdict(list)
    for sticker_id, sticker in stickers.items():
        if sticker.get("player_id") is not None:
            player_stickers[str(sticker["player_id"])].append(str(sticker_id))

    players = {}
    for player_id, payload in raw_players.items():
        events = payload.get("events") if isinstance(payload.get("events"), dict) else {}
        team_ids = sorted(
            {
                str(event_payload.get("team"))
                for event_payload in events.values()
                if isinstance(event_payload, dict) and event_payload.get("team")
            }
        )
        players[player_id] = {
            "id": parse_int(player_id),
            "game_id": parse_int(player_id),
            "name": payload.get("name") or payload.get("code") or player_id,
            "code": payload.get("code"),
            "date_of_birth": normalize_dob(payload.get("dob")),
            "country_code": payload.get("geo"),
            "tournament_event_ids": sorted(str(event_id) for event_id in events.keys()),
            "team_ids": team_ids,
            "event_teams": {
                str(event_id): str(event_payload.get("team"))
                for event_id, event_payload in events.items()
                if isinstance(event_payload, dict) and event_payload.get("team")
            },
            "sticker_ids": sorted(set(player_stickers.get(player_id, []))),
            "search_slug": slugify(payload.get("name") or payload.get("code") or player_id),
        }
    return players


def build_team_entities(
    raw_teams: dict[str, dict[str, Any]],
    raw_players: dict[str, dict[str, Any]],
    stickers: dict[str, dict[str, Any]],
    patches: dict[str, dict[str, Any]],
    graffiti: dict[str, dict[str, Any]],
    localizer: Localizer,
) -> dict[str, dict[str, Any]]:
    team_name_candidates: defaultdict[str, list[str]] = defaultdict(list)
    team_stickers: defaultdict[str, list[str]] = defaultdict(list)
    team_patches: defaultdict[str, list[str]] = defaultdict(list)
    team_graffiti: defaultdict[str, list[str]] = defaultdict(list)
    team_events: defaultdict[str, set[str]] = defaultdict(set)
    team_players: defaultdict[str, set[str]] = defaultdict(set)

    for group_name, entities, bucket in (
        ("stickers", stickers, team_stickers),
        ("patches", patches, team_patches),
        ("graffiti", graffiti, team_graffiti),
    ):
        for entity_id, entity in entities.items():
            team_id = entity.get("team_id")
            if team_id is None:
                continue
            team_key = str(team_id)
            bucket[team_key].append(str(entity_id))
            left, _ = split_pipe_name(entity.get("name"))
            if left:
                team_name_candidates[team_key].append(left)
            if entity.get("tournament_event_id") is not None:
                team_events[team_key].add(str(entity["tournament_event_id"]))

    for player_id, payload in raw_players.items():
        events = payload.get("events") if isinstance(payload.get("events"), dict) else {}
        for event_id, event_payload in events.items():
            if not isinstance(event_payload, dict) or not event_payload.get("team"):
                continue
            team_key = str(event_payload["team"])
            team_events[team_key].add(str(event_id))
            team_players[team_key].add(str(player_id))

    teams = {}
    for team_id, payload in raw_teams.items():
        display_name = most_common_nonempty(team_name_candidates.get(team_id, [])) or payload.get("tag") or team_id
        teams[team_id] = {
            "id": parse_int(team_id),
            "game_id": parse_int(team_id),
            "tag": payload.get("tag"),
            "name": display_name,
            "country_code": payload.get("geo"),
            "tournament_event_ids": sorted(team_events.get(team_id, set())),
            "player_ids": sorted(team_players.get(team_id, set())),
            "sticker_ids": sorted(set(team_stickers.get(team_id, []))),
            "patch_ids": sorted(set(team_patches.get(team_id, []))),
            "graffiti_ids": sorted(set(team_graffiti.get(team_id, []))),
            "search_slug": slugify(display_name or payload.get("tag") or team_id),
        }
    return teams


def build_tournament_entities(
    raw_event_results: dict[str, dict[str, Any]],
    containers: dict[str, dict[str, Any]],
    stickers: dict[str, dict[str, Any]],
    patches: dict[str, dict[str, Any]],
    graffiti: dict[str, dict[str, Any]],
    teams: dict[str, dict[str, Any]],
    players: dict[str, dict[str, Any]],
    localizer: Localizer,
) -> dict[str, dict[str, Any]]:
    event_name_candidates: defaultdict[str, list[str]] = defaultdict(list)
    event_slug_candidates: defaultdict[str, list[str]] = defaultdict(list)
    event_containers: defaultdict[str, list[str]] = defaultdict(list)
    event_stickers: defaultdict[str, list[str]] = defaultdict(list)
    event_patches: defaultdict[str, list[str]] = defaultdict(list)
    event_graffiti: defaultdict[str, list[str]] = defaultdict(list)
    event_players: defaultdict[str, set[str]] = defaultdict(set)

    for container_id, container in containers.items():
        event_id = container.get("tournament_event_id")
        if event_id is None:
            continue
        event_key = str(event_id)
        event_containers[event_key].append(str(container_id))
        event_name = extract_event_display_candidate(container.get("name"))
        if event_name:
            event_name_candidates[event_key].append(event_name)
        slug = extract_event_slug_from_codename(container.get("codename"))
        if slug:
            event_slug_candidates[event_key].append(slug)

    for entities, bucket in (
        (stickers, event_stickers),
        (patches, event_patches),
        (graffiti, event_graffiti),
    ):
        for entity_id, entity in entities.items():
            event_id = entity.get("tournament_event_id")
            if event_id is None:
                continue
            event_key = str(event_id)
            bucket[event_key].append(str(entity_id))
            event_name = extract_event_display_candidate(entity.get("name"))
            if event_name:
                event_name_candidates[event_key].append(event_name)
            slug = extract_event_slug_from_codename(entity.get("codename"))
            if slug:
                event_slug_candidates[event_key].append(slug)
            if entity.get("player_id") is not None:
                event_players[event_key].add(str(entity["player_id"]))

    for player_id, player in players.items():
        for event_id in player["tournament_event_ids"]:
            event_players[str(event_id)].add(str(player_id))

    event_ids = sorted(
        {
            *raw_event_results.keys(),
            *event_containers.keys(),
            *event_stickers.keys(),
            *event_patches.keys(),
            *event_graffiti.keys(),
            *event_players.keys(),
        },
        key=lambda value: int(value),
    )

    tournaments = {}
    for event_id in event_ids:
        payload = raw_event_results.get(event_id, {})
        place_names_raw = payload.get("place_names") if isinstance(payload.get("place_names"), dict) else {}
        place_names = {
            str(place_code): localizer.resolve(token) or token
            for place_code, token in place_names_raw.items()
        }
        display_name = most_common_nonempty(event_name_candidates.get(event_id, []))
        slug = most_common_nonempty(event_slug_candidates.get(event_id, []))
        if not slug and display_name:
            slug = slugify(display_name)
        if not slug:
            slug = f"event-{event_id}"
        team_results = []
        team_places = payload.get("team_places") if isinstance(payload.get("team_places"), dict) else {}
        for team_id, place_code in sorted(team_places.items(), key=lambda pair: int(pair[0])):
            team_key = str(parse_int(team_id) or team_id)
            team = teams.get(team_key, {})
            team_results.append(
                {
                    "team_id": parse_int(team_key),
                    "team_tag": team.get("tag"),
                    "team_name": team.get("name"),
                    "place_code": str(place_code),
                    "place_name": place_names.get(str(place_code)),
                }
            )
        tournaments[event_id] = {
            "id": parse_int(event_id),
            "game_id": parse_int(event_id),
            "slug": slug,
            "name": display_name or slug,
            "year": parse_int(re.search(r"(19|20)\d{2}", display_name or slug or "") .group(0)) if re.search(r"(19|20)\d{2}", display_name or slug or "") else None,
            "place_names": place_names,
            "team_results": team_results,
            "team_ids": sorted({str(result["team_id"]) for result in team_results if result["team_id"] is not None}),
            "player_ids": sorted(event_players.get(event_id, set())),
            "container_ids": sorted(set(event_containers.get(event_id, []))),
            "sticker_ids": sorted(set(event_stickers.get(event_id, []))),
            "patch_ids": sorted(set(event_patches.get(event_id, []))),
            "graffiti_ids": sorted(set(event_graffiti.get(event_id, []))),
            "search_slug": slugify(display_name or slug or event_id),
        }
    return tournaments


def build_asset_entities(
    core: dict[str, Any],
    weapons: dict[str, dict[str, Any]],
    containers: dict[str, dict[str, Any]],
    agents: dict[str, dict[str, Any]],
    tools: dict[str, dict[str, Any]],
    charms: dict[str, dict[str, Any]],
    music_kits: dict[str, dict[str, Any]],
    stickers: dict[str, dict[str, Any]],
    patches: dict[str, dict[str, Any]],
    graffiti: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    assets = {}
    resolved_items = core["resolved_items"]

    def add_asset(entity_type: str, entity_id: str, name: str, codename: str | None, refs: dict[str, Any]) -> None:
        if not refs:
            return
        asset_id = f"{entity_type}__{entity_id}"
        assets[asset_id] = {
            "id": asset_id,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "name": name,
            "codename": codename,
            "refs": refs,
        }

    for entity_type, entities in (
        ("weapon", weapons),
        ("container", containers),
        ("agent", agents),
        ("tool", tools),
    ):
        for entity_id, entity in entities.items():
            resolved = resolved_items.get(str(entity_id), {}).get("resolved", {})
            add_asset(entity_type, str(entity_id), entity["name"], entity.get("codename"), extract_item_asset_refs(resolved))

    for entity_id, entity in charms.items():
        resolved = core["keychains"].get(str(entity_id), {}).get("resolved", {})
        add_asset("charm", str(entity_id), entity["name"], entity.get("codename"), extract_item_asset_refs(resolved))

    for entity_id, entity in music_kits.items():
        resolved = core["music_definitions"].get(str(entity_id), {}).get("resolved", {})
        add_asset("music-kit", str(entity_id), entity["name"], entity.get("codename"), extract_item_asset_refs(resolved))

    for entity_type, entities in (
        ("sticker", stickers),
        ("patch", patches),
        ("graffiti", graffiti),
    ):
        for entity_id, entity in entities.items():
            refs = {}
            if entity.get("material"):
                refs["material"] = entity["material"]
            add_asset(entity_type, str(entity_id), entity["name"], entity.get("codename"), refs)

    return assets


def build_relations(
    skins: dict[str, dict[str, Any]],
    skin_variants: dict[str, dict[str, Any]],
    collections: dict[str, dict[str, Any]],
    containers: dict[str, dict[str, Any]],
    stickers: dict[str, dict[str, Any]],
    patches: dict[str, dict[str, Any]],
    graffiti: dict[str, dict[str, Any]],
    tournaments: dict[str, dict[str, Any]],
    teams: dict[str, dict[str, Any]],
    players: dict[str, dict[str, Any]],
    skin_relations: dict[str, Any],
) -> dict[str, Any]:
    skin_to_sources = {}
    skin_to_variants = {}
    collection_to_skins = defaultdict(list)
    container_to_drops = {}
    container_to_skins = defaultdict(list)
    sticker_to_team = defaultdict(list)
    sticker_to_player = defaultdict(list)
    sticker_to_tournament = defaultdict(list)
    patch_to_team = defaultdict(list)
    patch_to_player = defaultdict(list)
    patch_to_tournament = defaultdict(list)
    graffiti_to_team = defaultdict(list)
    graffiti_to_player = defaultdict(list)
    graffiti_to_tournament = defaultdict(list)
    tournament_to_teams = {}
    tournament_to_players = {}
    tournament_to_containers = {}
    team_to_players = {}
    team_to_tournaments = {}
    team_to_stickers = {}
    team_to_patches = {}
    team_to_graffiti = {}
    player_to_teams = {}
    player_to_tournaments = {}
    player_to_stickers = {}

    for skin_id, skin in skins.items():
        skin_to_sources[skin_id] = skin["sources"]
        skin_to_variants[skin_id] = sorted(skin.get("variant_ids", []))
        for source in skin["sources"]["collections"]:
            collection_to_skins[source["id"]].append(skin_id)
        for source in skin["sources"]["containers"]:
            container_to_skins[str(source["id"])].append(skin_id)

    for collection_id in collections:
        collection_to_skins[collection_id] = sorted(set(collection_to_skins.get(collection_id, [])))

    for container_id in containers:
        container_to_skins[str(container_id)] = sorted(set(container_to_skins.get(str(container_id), [])))

    for container_id, container in containers.items():
        container_to_drops[container_id] = container["contents"]

    for group_name, entities, to_team, to_player, to_tournament in (
        ("sticker", stickers, sticker_to_team, sticker_to_player, sticker_to_tournament),
        ("patch", patches, patch_to_team, patch_to_player, patch_to_tournament),
        ("graffiti", graffiti, graffiti_to_team, graffiti_to_player, graffiti_to_tournament),
    ):
        for entity_id, entity in entities.items():
            entity_id = str(entity_id)
            if entity.get("tournament_event_id") is not None:
                to_tournament[str(entity["tournament_event_id"])].append(entity_id)
            if entity.get("team_id") is not None:
                to_team[str(entity["team_id"])].append(entity_id)
            if entity.get("player_id") is not None:
                to_player[str(entity["player_id"])].append(entity_id)

    return {
        "skin-to-sources": skin_to_sources,
        "skin-to-variants": skin_to_variants,
        "collection-to-skins": dict(collection_to_skins),
        "container-to-skins": dict(container_to_skins or skin_relations.get("container_to_skins", {})),
        "container-to-drops": container_to_drops,
        "sticker-to-tournament": dict(sticker_to_tournament),
        "sticker-to-team": dict(sticker_to_team),
        "sticker-to-player": dict(sticker_to_player),
        "patch-to-tournament": dict(patch_to_tournament),
        "patch-to-team": dict(patch_to_team),
        "patch-to-player": dict(patch_to_player),
        "graffiti-to-tournament": dict(graffiti_to_tournament),
        "graffiti-to-team": dict(graffiti_to_team),
        "graffiti-to-player": dict(graffiti_to_player),
        "tournament-to-teams": {
            tournament_id: sorted(set(tournament["team_ids"]))
            for tournament_id, tournament in tournaments.items()
        },
        "tournament-to-players": {
            tournament_id: sorted(set(tournament["player_ids"]))
            for tournament_id, tournament in tournaments.items()
        },
        "tournament-to-containers": {
            tournament_id: sorted(set(tournament["container_ids"]))
            for tournament_id, tournament in tournaments.items()
        },
        "team-to-players": {
            team_id: sorted(set(team["player_ids"]))
            for team_id, team in teams.items()
        },
        "team-to-tournaments": {
            team_id: sorted(set(team["tournament_event_ids"]))
            for team_id, team in teams.items()
        },
        "team-to-stickers": {
            team_id: sorted(set(team["sticker_ids"]))
            for team_id, team in teams.items()
        },
        "team-to-patches": {
            team_id: sorted(set(team["patch_ids"]))
            for team_id, team in teams.items()
        },
        "team-to-graffiti": {
            team_id: sorted(set(team["graffiti_ids"]))
            for team_id, team in teams.items()
        },
        "player-to-teams": {
            player_id: sorted(set(player["team_ids"]))
            for player_id, player in players.items()
        },
        "player-to-tournaments": {
            player_id: sorted(set(player["tournament_event_ids"]))
            for player_id, player in players.items()
        },
        "player-to-stickers": {
            player_id: sorted(set(player["sticker_ids"]))
            for player_id, player in players.items()
        },
    }


def build_indexes(**entity_groups: dict[str, dict[str, Any]]) -> dict[str, Any]:
    finishes = entity_groups["finishes"]
    skins = entity_groups["skins"]
    skin_variants = entity_groups["skin_variants"]
    collections = entity_groups["collections"]
    containers = entity_groups["containers"]
    stickers = entity_groups["stickers"]
    patches = entity_groups["patches"]
    graffiti = entity_groups["graffiti"]
    special_drops = entity_groups["special_drops"]
    tournaments = entity_groups["tournaments"]
    teams = entity_groups["teams"]
    players = entity_groups["players"]
    agents = entity_groups["agents"]
    charms = entity_groups["charms"]
    music_kits = entity_groups["music_kits"]
    weapons = entity_groups["weapons"]

    by_weapon = defaultdict(list)
    by_finish = defaultdict(list)
    by_collection = defaultdict(list)
    by_container = {}
    by_rarity = defaultdict(lambda: defaultdict(list))
    by_finish_style = defaultdict(list)
    by_quality = defaultdict(list)
    by_exterior = defaultdict(list)
    by_tournament = defaultdict(lambda: defaultdict(list))
    by_team = defaultdict(lambda: defaultdict(list))
    by_player = defaultdict(lambda: defaultdict(list))
    by_slug = defaultdict(list)
    by_market_hash_name = defaultdict(list)

    for finish_id, finish in finishes.items():
        rarity_ref = finish.get("rarity_ref")
        if rarity_ref:
            by_rarity[str(rarity_ref)]["finishes"].append(str(finish_id))
        style_code = finish.get("style_code")
        if style_code is not None:
            by_finish_style[str(style_code)].append(str(finish_id))
        by_slug[finish["search_slug"]].append({"kind": "finish", "id": str(finish_id)})
        by_market_hash_name[finish["name"]].append({"kind": "finish", "id": str(finish_id)})

    for skin_id, skin in skins.items():
        by_weapon[str(skin["weapon"]["id"])].append(skin_id)
        by_finish[str(skin["finish"]["id"])].append(skin_id)
        rarity_ref = skin["finish"].get("rarity_ref")
        if rarity_ref:
            by_rarity[str(rarity_ref)]["skins"].append(skin_id)
        for source in skin["sources"]["collections"]:
            by_collection[source["id"]].append(skin_id)
        by_slug[skin["search_slug"]].append({"kind": "skin", "id": skin_id})
        by_market_hash_name[skin["name"]].append({"kind": "skin", "id": skin_id})

    for variant_id, variant in skin_variants.items():
        by_quality[variant["quality"]].append(variant_id)
        by_exterior[variant["exterior"]].append(variant_id)
        by_slug[variant["search_slug"]].append({"kind": "skin-variant", "id": variant_id})
        by_market_hash_name[variant["market_hash_name"]].append({"kind": "skin-variant", "id": variant_id})

    for collection_id, collection in collections.items():
        by_slug[collection["search_slug"]].append({"kind": "collection", "id": collection_id})
        by_market_hash_name[collection["name"]].append({"kind": "collection", "id": collection_id})

    for container_id, container in containers.items():
        by_container[str(container_id)] = container["contents"]
        if container.get("tournament_event_id") is not None:
            by_tournament[str(container["tournament_event_id"])]["containers"].append(str(container_id))
        by_slug[container["search_slug"]].append({"kind": "container", "id": str(container_id)})
        by_market_hash_name[container["name"]].append({"kind": "container", "id": str(container_id)})

    for sticker_id, sticker in stickers.items():
        rarity_ref = sticker.get("rarity_ref")
        if rarity_ref:
            by_rarity[str(rarity_ref)]["stickers"].append(str(sticker_id))
        if sticker.get("tournament_event_id") is not None:
            by_tournament[str(sticker["tournament_event_id"])]["stickers"].append(str(sticker_id))
        if sticker.get("team_id") is not None:
            by_team[str(sticker["team_id"])]["stickers"].append(str(sticker_id))
        if sticker.get("player_id") is not None:
            by_player[str(sticker["player_id"])]["stickers"].append(str(sticker_id))
        by_slug[sticker["search_slug"]].append({"kind": "sticker", "id": str(sticker_id)})
        by_market_hash_name[sticker["name"]].append({"kind": "sticker", "id": str(sticker_id)})

    for patch_id, patch in patches.items():
        rarity_ref = patch.get("rarity_ref")
        if rarity_ref:
            by_rarity[str(rarity_ref)]["patches"].append(str(patch_id))
        if patch.get("tournament_event_id") is not None:
            by_tournament[str(patch["tournament_event_id"])]["patches"].append(str(patch_id))
        if patch.get("team_id") is not None:
            by_team[str(patch["team_id"])]["patches"].append(str(patch_id))
        if patch.get("player_id") is not None:
            by_player[str(patch["player_id"])]["patches"].append(str(patch_id))
        by_slug[patch["search_slug"]].append({"kind": "patch", "id": str(patch_id)})
        by_market_hash_name[patch["name"]].append({"kind": "patch", "id": str(patch_id)})

    for graffiti_id, graffiti_item in graffiti.items():
        rarity_ref = graffiti_item.get("rarity_ref")
        if rarity_ref:
            by_rarity[str(rarity_ref)]["graffiti"].append(str(graffiti_id))
        if graffiti_item.get("tournament_event_id") is not None:
            by_tournament[str(graffiti_item["tournament_event_id"])]["graffiti"].append(str(graffiti_id))
        if graffiti_item.get("team_id") is not None:
            by_team[str(graffiti_item["team_id"])]["graffiti"].append(str(graffiti_id))
        if graffiti_item.get("player_id") is not None:
            by_player[str(graffiti_item["player_id"])]["graffiti"].append(str(graffiti_id))
        by_slug[graffiti_item["search_slug"]].append({"kind": "graffiti", "id": str(graffiti_id)})
        by_market_hash_name[graffiti_item["name"]].append({"kind": "graffiti", "id": str(graffiti_id)})

    for special_drop_id, special_drop in special_drops.items():
        by_slug[special_drop["search_slug"]].append({"kind": "special-drop", "id": str(special_drop_id)})
        by_market_hash_name[special_drop["name"]].append({"kind": "special-drop", "id": str(special_drop_id)})

    for tournament_id, tournament in tournaments.items():
        by_tournament[str(tournament_id)]["tournaments"].append(str(tournament_id))
        for team_id in tournament["team_ids"]:
            by_tournament[str(tournament_id)]["teams"].append(str(team_id))
        for player_id in tournament["player_ids"]:
            by_tournament[str(tournament_id)]["players"].append(str(player_id))
        by_slug[tournament["search_slug"]].append({"kind": "tournament", "id": str(tournament_id)})
        by_market_hash_name[tournament["name"]].append({"kind": "tournament", "id": str(tournament_id)})

    for team_id, team in teams.items():
        by_team[str(team_id)]["teams"].append(str(team_id))
        for player_id in team["player_ids"]:
            by_team[str(team_id)]["players"].append(str(player_id))
        for event_id in team["tournament_event_ids"]:
            by_team[str(team_id)]["tournaments"].append(str(event_id))
        by_slug[team["search_slug"]].append({"kind": "team", "id": str(team_id)})
        by_market_hash_name[team["name"]].append({"kind": "team", "id": str(team_id)})
        if team.get("tag"):
            by_market_hash_name[team["tag"]].append({"kind": "team", "id": str(team_id)})

    for player_id, player in players.items():
        by_player[str(player_id)]["players"].append(str(player_id))
        for team_id in player["team_ids"]:
            by_player[str(player_id)]["teams"].append(str(team_id))
        for event_id in player["tournament_event_ids"]:
            by_player[str(player_id)]["tournaments"].append(str(event_id))
        by_slug[player["search_slug"]].append({"kind": "player", "id": str(player_id)})
        by_market_hash_name[player["name"]].append({"kind": "player", "id": str(player_id)})
        if player.get("code"):
            by_market_hash_name[player["code"]].append({"kind": "player", "id": str(player_id)})

    for agent_id, agent in agents.items():
        rarity_ref = agent.get("rarity_ref")
        if rarity_ref:
            by_rarity[str(rarity_ref)]["agents"].append(str(agent_id))
        by_slug[agent["search_slug"]].append({"kind": "agent", "id": str(agent_id)})
        by_market_hash_name[agent["name"]].append({"kind": "agent", "id": str(agent_id)})

    for charm_id, charm in charms.items():
        rarity_ref = charm.get("rarity_ref")
        if rarity_ref:
            by_rarity[str(rarity_ref)]["charms"].append(str(charm_id))
        by_slug[charm["search_slug"]].append({"kind": "charm", "id": str(charm_id)})
        by_market_hash_name[charm["name"]].append({"kind": "charm", "id": str(charm_id)})

    for music_id, music in music_kits.items():
        by_slug[music["search_slug"]].append({"kind": "music-kit", "id": str(music_id)})
        by_market_hash_name[music["name"]].append({"kind": "music-kit", "id": str(music_id)})

    for weapon_id, weapon in weapons.items():
        by_slug[weapon["search_slug"]].append({"kind": "weapon", "id": str(weapon_id)})
        by_market_hash_name[weapon["name"]].append({"kind": "weapon", "id": str(weapon_id)})

    return {
        "by-weapon": {key: sorted(set(value)) for key, value in by_weapon.items()},
        "by-finish": {key: sorted(set(value)) for key, value in by_finish.items()},
        "by-collection": {key: sorted(set(value)) for key, value in by_collection.items()},
        "by-container": by_container,
        "by-rarity": {
            key: {kind: sorted(set(ids)) for kind, ids in buckets.items()}
            for key, buckets in by_rarity.items()
        },
        "by-finish-style": {key: sorted(set(value)) for key, value in by_finish_style.items()},
        "by-quality": {key: sorted(set(value)) for key, value in by_quality.items()},
        "by-exterior": {key: sorted(set(value)) for key, value in by_exterior.items()},
        "by-tournament": {
            key: {kind: sorted(set(ids)) for kind, ids in buckets.items()}
            for key, buckets in by_tournament.items()
        },
        "by-team": {
            key: {kind: sorted(set(ids)) for kind, ids in buckets.items()}
            for key, buckets in by_team.items()
        },
        "by-player": {
            key: {kind: sorted(set(ids)) for kind, ids in buckets.items()}
            for key, buckets in by_player.items()
        },
        "by-slug": {key: unique_list(value) for key, value in by_slug.items()},
        "by-market-hash-name": {key: unique_list(value) for key, value in by_market_hash_name.items()},
    }
