from __future__ import annotations

from collections import defaultdict
from typing import Any

from cs2_skins_api.normalize import Localizer
from cs2_skins_api.utils import slugify, unique_list


FINISH_STYLE_LABELS = {
    1: "Solid Color",
    2: "Hydrographic",
    3: "Spray-Paint",
    4: "Anodized",
    5: "Anodized Multicolored",
    6: "Anodized Airbrushed",
    7: "Custom Paint Job",
    8: "Patina",
    9: "Gunsmith",
}

CONSUMER_CONTAINER_GROUPS = {
    "weapon-case": "cases",
    "sticker-capsule": "capsules",
    "pin-capsule": "capsules",
    "souvenir-package": "souvenir-packages",
    "music-kit-box": "containers",
    "graffiti-box": "containers",
    "container": "containers",
}

LEGACY_KNIFE_POOL_WEAPONS = {
    "unusual_revolving_list": [500, 505, 506, 507, 508],
    "community_case_3_unusual": [509],
    "community_case_4_unusual": [515],
    "community_case_8_unusual": [512],
    "community_case_9_unusual": [516],
    "community_case_11_unusual": [514],
    "set_community_20_unusual": [519, 520, 522, 523],
    "set_community_23_unusual": [517, 518, 521, 525],
    "set_community_24_unusual": [503],
    "set_community_33_unusual": [526],
}

CHROMA_KNIFE_POOL_WEAPONS = {
    "community_case_6_unusual": [500, 505, 506, 507, 508],
    "spectrum_unusual": [509, 512, 514, 515, 516],
    "set_community_22_unusual": [519, 520, 522, 523],
    "set_community_35_unusual": [517, 518, 521, 525],
}

GAMMA_KNIFE_POOL_WEAPONS = {
    "community_case_13_unusual": [500, 505, 506, 507, 508],
    "gamma2_knives2_unusual": [517, 518, 521, 525],
}

LEGACY_KNIFE_PAINT_IDS = [5, 12, 38, 40, 42, 43, 44, 59, 72, 77, 98, 143, 175]
CHROMA_KNIFE_FAMILY_PAINT_IDS = [98, 409, 410, 411, 413, 414, 415, 416, 417, 418, 419, 420, 421]
GAMMA_KNIFE_FAMILY_PAINT_IDS = [568, 569, 570, 571, 572, 578, 579, 580, 581, 582]

GLOVE_POOL_RULES = {
    "community_case_15_unusual": "legacy-gloves",
    "set_community_19_unusual": "hydra-era-gloves",
    "set_glove_3_unusual": "broken-fang-gloves",
    "set_community_37_unusual": "volatile-gloves",
}

GLOVE_WEAPON_BY_FAMILY = {
    "bloodhound": 5027,
    "brokenfang": 4725,
    "handwrap": 5032,
    "hydra": 5035,
    "motorcycle": 5033,
    "slick": 5031,
    "specialist": 5034,
    "sporty": 5030,
}


def build_consumer_dataset(
    core: dict[str, Any],
    api: dict[str, Any],
    localizer: Localizer,
    rendered: dict[str, Any],
) -> dict[str, Any]:
    locales = sorted(localizer.tokens_by_locale)
    finish_name_map = build_finish_name_map(api["finishes"], localizer, locales)
    weapon_name_map = build_weapon_name_map(api["weapons"], localizer, locales)
    rarity_labels = build_rarity_label_map(core["enums"].get("rarities", {}), localizer, locales)

    special_pool_cards = build_special_pool_cards(core, api, localizer, locales, finish_name_map, weapon_name_map)
    weapon_cards = build_weapon_cards(
        api["weapons"],
        api["assets"],
        api["relations"],
        special_pool_cards,
        rendered,
        localizer,
        locales,
    )
    skin_cards = build_skin_cards(
        api["skins"],
        api["weapons"],
        api["finishes"],
        api["assets"],
        rendered,
        localizer,
        locales,
        finish_name_map,
        weapon_name_map,
    )
    variant_cards = build_variant_cards(api["skin_variants"], skin_cards, rendered)
    container_cards = build_container_cards(
        api["containers"],
        api["assets"],
        api["relations"],
        api["weapons"],
        api["finishes"],
        skin_cards,
        special_pool_cards,
        rendered,
        localizer,
        locales,
        rarity_labels,
    )
    collection_cards = build_collection_cards(api["collections"], api["relations"], api["assets"], localizer, locales)
    sticker_cards = build_decal_cards(api["stickers"], api["assets"], rendered, "sticker", localizer, locales)
    patch_cards = build_decal_cards(api["patches"], api["assets"], rendered, "patch", localizer, locales)
    graffiti_cards = build_decal_cards(api["graffiti"], api["assets"], rendered, "graffiti", localizer, locales)
    agent_cards = build_simple_cards(api["agents"], api["assets"], rendered, "agent", localizer, locales)
    charm_cards = build_simple_cards(api["charms"], api["assets"], rendered, "charm", localizer, locales)
    music_kit_cards = build_simple_cards(api["music_kits"], api["assets"], rendered, "music-kit", localizer, locales)
    tournament_cards = build_event_cards(api["tournaments"], api["relations"], localizer, locales)
    team_cards = build_team_cards(api["teams"], api["relations"], localizer, locales)
    player_cards = build_player_cards(api["players"], api["relations"])

    cards = {
        "weapons": weapon_cards,
        "skins": skin_cards,
        "skin-variants": variant_cards,
        **container_cards,
        "collections": collection_cards,
        "stickers": sticker_cards,
        "patches": patch_cards,
        "graffiti": graffiti_cards,
        "special-pools": special_pool_cards,
        "agents": agent_cards,
        "charms": charm_cards,
        "music-kits": music_kit_cards,
        "tournaments": tournament_cards,
        "teams": team_cards,
        "players": player_cards,
    }

    lists = build_consumer_lists(cards)
    browse = build_consumer_browse(cards)
    discovery = build_consumer_discovery(cards)
    facets = build_consumer_facets(cards, special_pool_cards)

    return {
        "cards": cards,
        "lists": lists,
        "browse": browse,
        "meta": {
            "discovery": discovery,
            "facets": facets,
        },
        "stats": {
            card_group: len(group_cards)
            for card_group, group_cards in cards.items()
        },
    }


def build_finish_name_map(
    finishes: dict[str, dict[str, Any]],
    localizer: Localizer,
    locales: list[str],
) -> dict[str, dict[str, str]]:
    return {
        str(finish_id): localized_values(localizer, finish.get("name_token"), finish.get("name"), locales)
        for finish_id, finish in finishes.items()
    }


def build_weapon_name_map(
    weapons: dict[str, dict[str, Any]],
    localizer: Localizer,
    locales: list[str],
) -> dict[str, dict[str, str]]:
    return {
        str(weapon_id): localized_values(localizer, weapon.get("name_token"), weapon.get("name"), locales)
        for weapon_id, weapon in weapons.items()
    }


def build_rarity_label_map(
    rarities: dict[str, dict[str, Any]],
    localizer: Localizer,
    locales: list[str],
) -> dict[str, dict[str, Any]]:
    labels = {}
    for rarity_id, payload in rarities.items():
        token = payload.get("loc_key_weapon") or payload.get("loc_key")
        labels[rarity_id] = {
            "id": rarity_id,
            "name": localizer.resolve(f"#{token}") if token else rarity_id.replace("-", " ").title(),
            "localized_names": localized_values(localizer, f"#{token}" if token else None, rarity_id.replace("-", " ").title(), locales),
            "color_ref": payload.get("color"),
            "value": payload.get("value"),
        }
    return labels


def build_special_pool_cards(
    core: dict[str, Any],
    api: dict[str, Any],
    localizer: Localizer,
    locales: list[str],
    finish_name_map: dict[str, dict[str, str]],
    weapon_name_map: dict[str, dict[str, str]],
) -> dict[str, dict[str, Any]]:
    paint_kits = core["paint_kits"]
    special_pools = {}
    for token, pool in api["special_drops"].items():
        exact_candidates = []
        finish_profiles = []
        pool_category = "special-item"
        expansion_status = "token-only"

        if token in GLOVE_POOL_RULES:
            pool_category = "glove"
            expansion_status = "exact-candidates"
            exact_candidates = build_glove_candidates(
                pool_id=token,
                pool_rule=GLOVE_POOL_RULES[token],
                paint_kits=paint_kits,
                weapons=api["weapons"],
                weapon_name_map=weapon_name_map,
                finish_name_map=finish_name_map,
                localizer=localizer,
                locales=locales,
            )
        elif token in LEGACY_KNIFE_POOL_WEAPONS:
            pool_category = "knife"
            expansion_status = "exact-candidates"
            exact_candidates = build_knife_candidates(
                pool_id=token,
                weapon_ids=LEGACY_KNIFE_POOL_WEAPONS[token],
                paint_kit_ids=LEGACY_KNIFE_PAINT_IDS,
                paint_kits=paint_kits,
                weapons=api["weapons"],
                weapon_name_map=weapon_name_map,
                finish_name_map=finish_name_map,
                localizer=localizer,
                locales=locales,
            )
        elif token in CHROMA_KNIFE_POOL_WEAPONS:
            pool_category = "knife"
            expansion_status = "finish-family"
            finish_profiles.append(
                build_finish_profile(
                    profile_id="chroma-knives",
                    label="Chroma Knife Finishes",
                    paint_kit_ids=CHROMA_KNIFE_FAMILY_PAINT_IDS,
                    finishes=api["finishes"],
                )
            )
        elif token in GAMMA_KNIFE_POOL_WEAPONS:
            pool_category = "knife"
            expansion_status = "finish-family"
            finish_profiles.append(
                build_finish_profile(
                    profile_id="gamma-knives",
                    label="Gamma Knife Finishes",
                    paint_kit_ids=GAMMA_KNIFE_FAMILY_PAINT_IDS,
                    finishes=api["finishes"],
                )
            )
        elif token == "all_entries_as_additional_drops":
            pool_category = "bonus-rule"
            expansion_status = "rule"
        elif token == "match_highlight_reel_keychain":
            pool_category = "bonus-rule"
            expansion_status = "rule"

        eligible_weapon_ids = unique_list(
            [
                candidate["weapon"]["id"]
                for candidate in exact_candidates
                if candidate.get("weapon", {}).get("id") is not None
            ]
            + LEGACY_KNIFE_POOL_WEAPONS.get(token, [])
            + CHROMA_KNIFE_POOL_WEAPONS.get(token, [])
            + GAMMA_KNIFE_POOL_WEAPONS.get(token, [])
        )

        name_token = first_nonempty(pool.get("display_name_tokens", []))
        footer_token = first_nonempty(pool.get("footer_tokens", []))
        special_pools[token] = {
            "id": token,
            "card_type": "special-pool",
            "pool_category": pool_category,
            "expansion_status": expansion_status,
            "name": pool["name"],
            "localized_names": localized_values(localizer, name_token, pool["name"], locales),
            "footer": first_nonempty(pool.get("footers", [])),
            "localized_footers": localized_values(localizer, footer_token, first_nonempty(pool.get("footers", [])), locales),
            "search_slug": pool.get("search_slug") or slugify(pool["name"]),
            "source_cases": [
                card_ref(
                    "cases",
                    container_id,
                    api["containers"][container_id]["name"],
                    api["containers"][container_id]["search_slug"],
                    "case",
                )
                for container_id in pool.get("source_container_ids", [])
                if container_id in api["containers"] and api["containers"][container_id]["container_kind"] == "weapon-case"
            ],
            "source_containers": [
                card_ref(
                    CONSUMER_CONTAINER_GROUPS.get(api["containers"][container_id]["container_kind"], "containers"),
                    container_id,
                    api["containers"][container_id]["name"],
                    api["containers"][container_id]["search_slug"],
                    api["containers"][container_id]["container_kind"],
                )
                for container_id in pool.get("source_container_ids", [])
                if container_id in api["containers"]
            ],
            "eligible_weapons": [
                {
                    "id": weapon_id,
                    "name": api["weapons"][str(weapon_id)]["name"],
                    "localized_names": weapon_name_map.get(str(weapon_id), {}),
                    "weapon_group": api["weapons"][str(weapon_id)]["weapon_group"],
                    "search_slug": api["weapons"][str(weapon_id)]["search_slug"],
                }
                for weapon_id in eligible_weapon_ids
                if str(weapon_id) in api["weapons"]
            ],
            "finish_profiles": finish_profiles,
            "candidate_items": exact_candidates,
        }
    return special_pools


def build_glove_candidates(
    pool_id: str,
    pool_rule: str,
    paint_kits: dict[str, dict[str, Any]],
    weapons: dict[str, dict[str, Any]],
    weapon_name_map: dict[str, dict[str, str]],
    finish_name_map: dict[str, dict[str, str]],
    localizer: Localizer,
    locales: list[str],
) -> list[dict[str, Any]]:
    candidates = []
    for paint in paint_kits.values():
        if classify_glove_pool(paint) != pool_rule:
            continue
        family = classify_glove_family(paint)
        weapon_id = GLOVE_WEAPON_BY_FAMILY.get(family)
        if weapon_id is None or str(weapon_id) not in weapons:
            continue
        candidates.append(
            build_candidate_item(
                weapon_id=weapon_id,
                paint_kit=paint,
                weapons=weapons,
                weapon_name_map=weapon_name_map,
                finish_name_map=finish_name_map,
                localizer=localizer,
                locales=locales,
                source_pool_id=pool_id,
                item_category="glove",
            )
        )
    return sorted(candidates, key=lambda row: (row["weapon"]["name"], row["finish"]["name"]))


def build_knife_candidates(
    pool_id: str,
    weapon_ids: list[int],
    paint_kit_ids: list[int],
    paint_kits: dict[str, dict[str, Any]],
    weapons: dict[str, dict[str, Any]],
    weapon_name_map: dict[str, dict[str, str]],
    finish_name_map: dict[str, dict[str, str]],
    localizer: Localizer,
    locales: list[str],
) -> list[dict[str, Any]]:
    candidates = []
    for weapon_id in weapon_ids:
        if str(weapon_id) not in weapons:
            continue
        for paint_kit_id in paint_kit_ids:
            paint = paint_kits.get(str(paint_kit_id))
            if paint is None:
                continue
            candidates.append(
                build_candidate_item(
                    weapon_id=weapon_id,
                    paint_kit=paint,
                    weapons=weapons,
                    weapon_name_map=weapon_name_map,
                    finish_name_map=finish_name_map,
                    localizer=localizer,
                    locales=locales,
                    source_pool_id=pool_id,
                    item_category="knife",
                )
            )
    return sorted(candidates, key=lambda row: (row["weapon"]["name"], row["finish"]["name"]))


def build_candidate_item(
    weapon_id: int,
    paint_kit: dict[str, Any],
    weapons: dict[str, dict[str, Any]],
    weapon_name_map: dict[str, dict[str, str]],
    finish_name_map: dict[str, dict[str, str]],
    localizer: Localizer,
    locales: list[str],
    source_pool_id: str,
    item_category: str,
) -> dict[str, Any]:
    weapon = weapons[str(weapon_id)]
    localized_names = combine_localized_maps(
        weapon_name_map.get(str(weapon_id), {}),
        finish_name_map.get(str(paint_kit["id"]), {}),
        locales,
    )
    finish_style_code = paint_kit.get("style_code")
    return {
        "id": f"{weapon_id}-{paint_kit['id']}",
        "category": item_category,
        "name": f"{weapon['name']} | {paint_kit['display_name'] or paint_kit['name']}",
        "localized_names": localized_names,
        "search_slug": slugify(f"{weapon['name']} {paint_kit['display_name'] or paint_kit['name']}"),
        "source_pool_id": source_pool_id,
        "weapon": {
            "id": weapon_id,
            "name": weapon["name"],
            "weapon_group": weapon["weapon_group"],
            "search_slug": weapon["search_slug"],
        },
        "finish": {
            "id": paint_kit["id"],
            "name": paint_kit["display_name"] or paint_kit["name"],
            "style_code": finish_style_code,
            "style_name": FINISH_STYLE_LABELS.get(finish_style_code),
            "rarity_ref": paint_kit.get("rarity_ref"),
        },
        "wear": {
            "min_float": paint_kit.get("wear_min"),
            "max_float": paint_kit.get("wear_max"),
        },
        "availability": {
            "normal": True,
            "stattrak": item_category == "knife",
            "souvenir": False,
        },
        "generation_notes": {
            "source_backed": False,
            "consumer_derived_from_pool": True,
        },
    }


def build_finish_profile(profile_id: str, label: str, paint_kit_ids: list[int], finishes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    entries = []
    for paint_kit_id in paint_kit_ids:
        finish = finishes.get(str(paint_kit_id))
        if finish is None:
            continue
        entries.append(
            {
                "id": finish["id"],
                "name": finish["name"],
                "search_slug": finish["search_slug"],
            }
        )
    return {
        "id": profile_id,
        "label": label,
        "finish_ids": [entry["id"] for entry in entries],
        "finish_names": sorted(set(entry["name"] for entry in entries)),
        "finishes": entries,
    }


def build_weapon_cards(
    weapons: dict[str, dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    relations: dict[str, Any],
    special_pools: dict[str, dict[str, Any]],
    rendered: dict[str, Any],
    localizer: Localizer,
    locales: list[str],
) -> dict[str, dict[str, Any]]:
    special_pool_ids_by_weapon = defaultdict(list)
    for pool_id, pool in special_pools.items():
        for weapon in pool.get("eligible_weapons", []):
            special_pool_ids_by_weapon[str(weapon["id"])].append(pool_id)

    skins_by_weapon = defaultdict(list)
    for skin_id, sources in relations.get("skin-to-sources", {}).items():
        weapon_id = str(skin_id).split("-", 1)[0]
        skins_by_weapon[weapon_id].append(skin_id)

    cards = {}
    for weapon_id, weapon in weapons.items():
        group = weapon["weapon_group"]
        card_type = "weapon"
        if group == "knife":
            card_type = "knife"
        elif group == "glove":
            card_type = "glove"
        cards[weapon_id] = {
            "id": weapon["id"],
            "card_type": card_type,
            "name": weapon["name"],
            "localized_names": localized_values(localizer, weapon.get("name_token"), weapon["name"], locales),
            "search_slug": weapon["search_slug"],
            "weapon_group": group,
            "side": weapon.get("side"),
            "type_name": weapon.get("type_name"),
            "description": weapon.get("description"),
            "media": generic_rendered_media_summary(rendered, "weapon", weapon_id, media_summary(assets, "weapon", weapon_id)),
            "supports_vanilla": group == "knife",
            "regular_skin_ids": sorted(set(skins_by_weapon.get(weapon_id, []))),
            "special_pool_ids": sorted(set(special_pool_ids_by_weapon.get(weapon_id, []))),
        }
    return cards


def build_skin_cards(
    skins: dict[str, dict[str, Any]],
    weapons: dict[str, dict[str, Any]],
    finishes: dict[str, dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    rendered: dict[str, Any],
    localizer: Localizer,
    locales: list[str],
    finish_name_map: dict[str, dict[str, str]],
    weapon_name_map: dict[str, dict[str, str]],
) -> dict[str, dict[str, Any]]:
    cards = {}
    for skin_id, skin in skins.items():
        weapon_id = str(skin["weapon"]["id"])
        finish_id = str(skin["finish"]["id"])
        finish = finishes[finish_id]
        weapon = weapons[weapon_id]
        finish_style_code = finish.get("style_code")
        rendered_skin = rendered.get("skins", {}).get(skin_id)
        cards[skin_id] = {
            "id": skin_id,
            "card_type": "weapon-skin",
            "name": skin["name"],
            "localized_names": combine_localized_maps(
                weapon_name_map.get(weapon_id, {}),
                finish_name_map.get(finish_id, {}),
                locales,
            ),
            "search_slug": skin["search_slug"],
            "weapon": {
                "id": weapon["id"],
                "name": weapon["name"],
                "localized_names": weapon_name_map.get(weapon_id, {}),
                "weapon_group": weapon["weapon_group"],
                "search_slug": weapon["search_slug"],
            },
            "finish": {
                "id": finish["id"],
                "name": finish["name"],
                "localized_names": finish_name_map.get(finish_id, {}),
                "style_code": finish_style_code,
                "style_name": FINISH_STYLE_LABELS.get(finish_style_code),
                "catalog_id": finish["id"],
                "rarity_ref": finish.get("rarity_ref"),
                "wear": finish.get("wear"),
            },
            "wear": skin["wear"],
            "available_exteriors": skin.get("supported_exteriors", []),
            "availability": skin.get("availability", {}),
            "sources": build_skin_sources(skin),
            "variant_ids": sorted(skin.get("variant_ids", [])),
            "media": skin_media_summary(assets, rendered_skin, weapon_id),
        }
    return cards


def build_variant_cards(
    variants: dict[str, dict[str, Any]],
    skin_cards: dict[str, dict[str, Any]],
    rendered: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    cards = {}
    for variant_id, variant in variants.items():
        skin = skin_cards.get(variant["skin_id"])
        rendered_variant = rendered.get("skin_variants", {}).get(variant_id)
        cards[variant_id] = {
            "id": variant_id,
            "card_type": "skin-variant",
            "skin_id": variant["skin_id"],
            "name": variant["market_hash_name"],
            "search_slug": variant["search_slug"],
            "market_hash_name": variant["market_hash_name"],
            "quality": variant["quality"],
            "quality_name": variant["quality_name"],
            "exterior": variant["exterior"],
            "exterior_name": variant["exterior_name"],
            "skin_name": skin["name"] if skin else None,
            "media": skin_variant_media_summary(rendered_variant),
        }
    return cards


def build_container_cards(
    containers: dict[str, dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    relations: dict[str, Any],
    weapons: dict[str, dict[str, Any]],
    finishes: dict[str, dict[str, Any]],
    skin_cards: dict[str, dict[str, Any]],
    special_pools: dict[str, dict[str, Any]],
    rendered: dict[str, Any],
    localizer: Localizer,
    locales: list[str],
    rarity_labels: dict[str, dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    grouped_cards: dict[str, dict[str, dict[str, Any]]] = {
        "cases": {},
        "capsules": {},
        "souvenir-packages": {},
        "containers": {},
    }
    for container_id, container in containers.items():
        group = CONSUMER_CONTAINER_GROUPS.get(container["container_kind"], "containers")
        card_type = group[:-1] if group.endswith("s") else group
        by_rarity = defaultdict(list)
        special_pool_refs = []
        drop_summaries = []
        for drop in relations.get("container-to-drops", {}).get(container_id, []):
            if drop["kind"] == "skin":
                skin_id = drop["skin_id"]
                skin_card = skin_cards.get(skin_id)
                if skin_card is None:
                    weapon = weapons.get(str(drop["weapon_id"]))
                    finish = finishes.get(str(drop["paint_kit_id"]))
                    name = f"{weapon['name']} | {finish['name']}" if weapon and finish else skin_id
                    item = card_ref("skins", skin_id, name, slugify(name), "weapon-skin")
                else:
                    item = card_ref("skins", skin_id, skin_card["name"], skin_card["search_slug"], skin_card["card_type"])
                if drop.get("tier"):
                    by_rarity[drop["tier"]].append(item)
                drop_summaries.append({**item, "tier": drop.get("tier")})
            elif drop["kind"] == "special-drop":
                pool = special_pools.get(drop["special_drop_id"])
                if pool:
                    item = card_ref("special-pools", pool["id"], pool["name"], pool["search_slug"], pool["card_type"])
                    special_pool_refs.append(item)
                    drop_summaries.append({**item, "tier": drop.get("tier")})
            else:
                drop_summaries.append(
                    {
                        "id": drop.get("item_definition_id") or drop.get("sticker_id") or drop.get("graffiti_id") or drop.get("music_kit_id"),
                        "item_kind": drop["kind"],
                        "tier": drop.get("tier"),
                    }
                )

        grouped_cards[group][container_id] = {
            "id": container["id"],
            "card_type": card_type,
            "name": container["name"],
            "localized_names": localized_values(localizer, container.get("name_token"), container["name"], locales),
            "search_slug": container["search_slug"],
            "container_kind": container["container_kind"],
            "series_id": container.get("series_id"),
            "tournament_event_id": container.get("tournament_event_id"),
            "description": container.get("description"),
            "contents_source": container.get("contents_source"),
            "media": generic_rendered_media_summary(
                rendered,
                "container",
                container_id,
                media_summary(assets, "container", container_id),
            ),
            "rare_special_item": {
                "name": container.get("rare_special_item", {}).get("name"),
                "localized_names": localized_values(
                    localizer,
                    container.get("rare_special_item", {}).get("name_token"),
                    container.get("rare_special_item", {}).get("name"),
                    locales,
                ),
                "footer": container.get("rare_special_item", {}).get("footer"),
                "localized_footers": localized_values(
                    localizer,
                    container.get("rare_special_item", {}).get("footer_token"),
                    container.get("rare_special_item", {}).get("footer"),
                    locales,
                ),
                "special_pool_ids": [item["id"] for item in special_pool_refs],
            },
            "contents": {
                "item_count": len(container.get("contents", [])),
                "skin_count": len(relations.get("container-to-skins", {}).get(container_id, [])),
                "special_pool_count": len(special_pool_refs),
                "by_rarity": [
                    {
                        "tier": tier,
                        "label": rarity_labels.get(tier, {}).get("name", tier.replace("-", " ").title()),
                        "localized_labels": rarity_labels.get(tier, {}).get("localized_names", {}),
                        "items": sorted(entries, key=lambda row: row["name"]),
                    }
                    for tier, entries in sorted(by_rarity.items())
                ],
                "drops": drop_summaries,
            },
            "skin_ids": sorted(relations.get("container-to-skins", {}).get(container_id, [])),
            "special_pools": sorted(special_pool_refs, key=lambda row: row["name"]),
        }
    return grouped_cards


def build_collection_cards(
    collections: dict[str, dict[str, Any]],
    relations: dict[str, Any],
    assets: dict[str, dict[str, Any]],
    localizer: Localizer,
    locales: list[str],
) -> dict[str, dict[str, Any]]:
    cards = {}
    for collection_id, collection in collections.items():
        cards[collection_id] = {
            "id": collection["id"],
            "card_type": "collection",
            "name": collection["name"],
            "localized_names": localized_values(localizer, collection.get("name_token"), collection["name"], locales),
            "search_slug": collection["search_slug"],
            "description": collection.get("description"),
            "skin_ids": sorted(relations.get("collection-to-skins", {}).get(collection_id, [])),
            "media": media_summary(assets, "collection", collection_id),
        }
    return cards


def build_decal_cards(
    entities: dict[str, dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    rendered: dict[str, Any],
    card_type: str,
    localizer: Localizer,
    locales: list[str],
) -> dict[str, dict[str, Any]]:
    cards = {}
    for entity_id, entity in entities.items():
        cards[entity_id] = {
            "id": entity["id"],
            "card_type": card_type,
            "name": entity["name"],
            "localized_names": localized_values(localizer, None, entity["name"], locales),
            "search_slug": entity["search_slug"],
            "description": entity.get("description"),
            "association": entity.get("association"),
            "finish": entity.get("finish"),
            "tournament_event_id": entity.get("tournament_event_id"),
            "team_id": entity.get("team_id"),
            "player_id": entity.get("player_id"),
            "rarity_ref": entity.get("rarity_ref"),
            "media": generic_rendered_media_summary(rendered, card_type, entity_id, media_summary(assets, card_type, entity_id)),
        }
    return cards


def build_simple_cards(
    entities: dict[str, dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    rendered: dict[str, Any],
    card_type: str,
    localizer: Localizer,
    locales: list[str],
) -> dict[str, dict[str, Any]]:
    cards = {}
    for entity_id, entity in entities.items():
        cards[entity_id] = {
            "id": entity["id"],
            "card_type": card_type,
            "name": entity["name"],
            "localized_names": localized_values(localizer, None, entity["name"], locales),
            "search_slug": entity["search_slug"],
            "description": entity.get("description"),
            "media": generic_rendered_media_summary(rendered, card_type, entity_id, media_summary(assets, card_type, entity_id)),
        }
    return cards


def build_event_cards(
    tournaments: dict[str, dict[str, Any]],
    relations: dict[str, Any],
    localizer: Localizer,
    locales: list[str],
) -> dict[str, dict[str, Any]]:
    cards = {}
    for tournament_id, tournament in tournaments.items():
        cards[tournament_id] = {
            "id": tournament["id"],
            "card_type": "tournament",
            "name": tournament["name"],
            "localized_names": localized_values(localizer, None, tournament["name"], locales),
            "search_slug": tournament["search_slug"],
            "year": tournament.get("year"),
            "team_ids": sorted(relations.get("tournament-to-teams", {}).get(tournament_id, [])),
            "player_ids": sorted(relations.get("tournament-to-players", {}).get(tournament_id, [])),
            "container_ids": sorted(relations.get("tournament-to-containers", {}).get(tournament_id, [])),
        }
    return cards


def build_team_cards(
    teams: dict[str, dict[str, Any]],
    relations: dict[str, Any],
    localizer: Localizer,
    locales: list[str],
) -> dict[str, dict[str, Any]]:
    cards = {}
    for team_id, team in teams.items():
        cards[team_id] = {
            "id": team["id"],
            "card_type": "team",
            "name": team["name"],
            "localized_names": localized_values(localizer, None, team["name"], locales),
            "search_slug": team["search_slug"],
            "code": team.get("code"),
            "country_code": team.get("country_code"),
            "player_ids": sorted(relations.get("team-to-players", {}).get(team_id, [])),
            "tournament_ids": sorted(relations.get("team-to-tournaments", {}).get(team_id, [])),
        }
    return cards


def build_player_cards(players: dict[str, dict[str, Any]], relations: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cards = {}
    for player_id, player in players.items():
        cards[player_id] = {
            "id": player["id"],
            "card_type": "player",
            "name": player["name"],
            "search_slug": player["search_slug"],
            "code": player.get("code"),
            "country_code": player.get("country_code"),
            "team_ids": sorted(relations.get("player-to-teams", {}).get(player_id, [])),
            "tournament_ids": sorted(relations.get("player-to-tournaments", {}).get(player_id, [])),
        }
    return cards


def build_skin_sources(skin: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    cases = []
    capsules = []
    souvenir_packages = []
    containers = []
    for container in skin.get("sources", {}).get("containers", []):
        ref = {
            "id": container["id"],
            "name": container["name"],
            "kind": container["kind"],
            "tier": container.get("tier"),
            "flags": container.get("flags", []),
        }
        if container["kind"] == "weapon-case":
            cases.append(ref)
        elif container["kind"] == "souvenir-package":
            souvenir_packages.append(ref)
        elif container["kind"] == "sticker-capsule":
            capsules.append(ref)
        else:
            containers.append(ref)
    return {
        "collections": skin.get("sources", {}).get("collections", []),
        "cases": unique_list(cases),
        "capsules": unique_list(capsules),
        "souvenir_packages": unique_list(souvenir_packages),
        "containers": unique_list(containers),
    }


def build_consumer_lists(cards: dict[str, dict[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    lists: dict[str, dict[str, Any]] = {
        "by-type": {},
        "by-weapon": defaultdict(list),
        "by-finish": defaultdict(list),
        "by-case": defaultdict(list),
        "by-collection": defaultdict(list),
        "by-search-slug": defaultdict(list),
        "by-market-hash-name": {},
    }

    for group_name, group_cards in cards.items():
        refs = []
        for card_id, card in group_cards.items():
            ref = card_ref(group_name, card_id, card.get("name") or str(card_id), card.get("search_slug"), card["card_type"])
            refs.append(ref)
            if card.get("search_slug"):
                lists["by-search-slug"][card["search_slug"]].append(ref)
        lists["by-type"][group_name] = sorted(refs, key=lambda row: row["name"])

    for skin_id, card in cards.get("skins", {}).items():
        weapon_id = str(card["weapon"]["id"])
        finish_id = str(card["finish"]["id"])
        ref = card_ref("skins", skin_id, card["name"], card["search_slug"], card["card_type"])
        lists["by-weapon"][weapon_id].append(ref)
        lists["by-finish"][finish_id].append(ref)
        for source in card.get("sources", {}).get("cases", []):
            lists["by-case"][str(source["id"])].append(ref)
        for source in card.get("sources", {}).get("collections", []):
            lists["by-collection"][str(source["id"])].append(ref)

    for variant_id, card in cards.get("skin-variants", {}).items():
        lists["by-market-hash-name"][card["market_hash_name"]] = [
            card_ref("skin-variants", variant_id, card["name"], card["search_slug"], card["card_type"])
        ]

    return {
        list_name: normalize_list_payload(payload)
        for list_name, payload in lists.items()
    }


def build_consumer_browse(cards: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    def refs(group_name: str) -> list[dict[str, Any]]:
        group_cards = cards.get(group_name, {})
        return sorted(
            [
                card_ref(group_name, card_id, card.get("name") or str(card_id), card.get("search_slug"), card["card_type"])
                for card_id, card in group_cards.items()
            ],
            key=lambda row: row["name"],
        )

    return {
        "home": {
            "categories": [
                {"id": "skins", "count": len(cards.get("skins", {})), "path": "data/api/consumer/cards/skins/"},
                {"id": "cases", "count": len(cards.get("cases", {})), "path": "data/api/consumer/cards/cases/"},
                {"id": "capsules", "count": len(cards.get("capsules", {})), "path": "data/api/consumer/cards/capsules/"},
                {"id": "souvenir-packages", "count": len(cards.get("souvenir-packages", {})), "path": "data/api/consumer/cards/souvenir-packages/"},
                {"id": "weapons", "count": len(cards.get("weapons", {})), "path": "data/api/consumer/cards/weapons/"},
                {"id": "collections", "count": len(cards.get("collections", {})), "path": "data/api/consumer/cards/collections/"},
                {"id": "stickers", "count": len(cards.get("stickers", {})), "path": "data/api/consumer/cards/stickers/"},
                {"id": "special-pools", "count": len(cards.get("special-pools", {})), "path": "data/api/consumer/cards/special-pools/"},
            ]
        },
        "categories": {
            "groups": [
                {"id": group_name, "count": len(group_cards)}
                for group_name, group_cards in sorted(cards.items())
            ]
        },
        "skins": {"items": refs("skins")},
        "cases": {"items": refs("cases")},
        "capsules": {"items": refs("capsules")},
        "souvenir-packages": {"items": refs("souvenir-packages")},
        "weapons": {"items": refs("weapons")},
        "collections": {"items": refs("collections")},
        "stickers": {"items": refs("stickers")},
        "agents": {"items": refs("agents")},
        "charms": {"items": refs("charms")},
        "music-kits": {"items": refs("music-kits")},
        "tournaments": {"items": refs("tournaments")},
        "special-pools": {"items": refs("special-pools")},
    }


def build_consumer_discovery(cards: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    return {
        "entrypoints": {
            "home": "data/api/consumer/browse/home.json",
            "skins": "data/api/consumer/cards/skins/<skin_id>.json",
            "skin_variants": "data/api/consumer/cards/skin-variants/<variant_id>.json",
            "cases": "data/api/consumer/cards/cases/<container_id>.json",
            "capsules": "data/api/consumer/cards/capsules/<container_id>.json",
            "souvenir_packages": "data/api/consumer/cards/souvenir-packages/<container_id>.json",
            "weapons": "data/api/consumer/cards/weapons/<weapon_id>.json",
            "collections": "data/api/consumer/cards/collections/<collection_id>.json",
            "special_pools": "data/api/consumer/cards/special-pools/<token>.json",
        },
        "counts": {
            group_name: len(group_cards)
            for group_name, group_cards in cards.items()
        },
    }


def build_consumer_facets(cards: dict[str, dict[str, dict[str, Any]]], special_pools: dict[str, dict[str, Any]]) -> dict[str, Any]:
    weapon_groups = defaultdict(int)
    finish_styles = defaultdict(int)
    pool_categories = defaultdict(int)
    for card in cards.get("weapons", {}).values():
        weapon_groups[card["weapon_group"]] += 1
    for card in cards.get("skins", {}).values():
        style_name = card["finish"].get("style_name") or f"style-{card['finish'].get('style_code')}"
        finish_styles[style_name] += 1
    for pool in special_pools.values():
        pool_categories[pool["pool_category"]] += 1
    return {
        "weapon_groups": dict(sorted(weapon_groups.items())),
        "finish_styles": dict(sorted(finish_styles.items())),
        "special_pool_categories": dict(sorted(pool_categories.items())),
    }


def normalize_list_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return {
            key: sorted(value, key=lambda row: row["name"]) if isinstance(value, list) and value and isinstance(value[0], dict) and "name" in value[0] else value
            for key, value in payload.items()
        }
    return payload


def media_summary(
    assets: dict[str, dict[str, Any]],
    entity_type: str,
    entity_id: str | int,
    preview_status: str | None = None,
) -> dict[str, Any]:
    asset_id = f"{entity_type}__{entity_id}"
    asset = assets.get(asset_id)
    if asset is None:
        return {
            "asset_id": asset_id,
            "manifest_path": f"data/api/media/manifests/{asset_id}.json",
            "preview_status": preview_status or "unavailable",
            "images": [],
            "models": [],
        }
    images = []
    models = []
    for ref_key, paths in asset.get("resolved_refs", {}).items():
        if ref_key.startswith("image_"):
            images.extend(paths)
        elif ref_key == "material":
            images.extend(path for path in paths if path.endswith(".vtex_c"))
        elif ref_key.startswith("model_") or ref_key == "inventory_image_data.root_mdl":
            models.extend(paths)
    return {
        "asset_id": asset_id,
        "manifest_path": f"data/api/media/manifests/{asset_id}.json",
        "preview_status": preview_status or ("image" if images else "model-only" if models else "unavailable"),
        "images": unique_list(images),
        "models": unique_list(models),
    }


def generic_rendered_media_summary(
    rendered: dict[str, Any],
    entity_type: str,
    entity_id: str | int,
    fallback: dict[str, Any],
) -> dict[str, Any]:
    folder_name = rendered_folder_name(entity_type)
    if folder_name is None:
        return fallback
    rendered_entity = rendered.get("entities", {}).get(folder_name, {}).get(str(entity_id))
    if rendered_entity is None:
        return {
            **fallback,
            "primary_image_png": None,
            "source_texture_path": None,
        }
    return {
        "asset_id": fallback.get("asset_id"),
        "manifest_path": rendered_entity["manifest_path"],
        "preview_status": rendered_entity.get("preview_status", "rendered"),
        "primary_image_png": rendered_entity.get("image_path"),
        "source_texture_path": rendered_entity.get("source_texture_path"),
        "images_png": [rendered_entity.get("image_path")] if rendered_entity.get("image_path") else [],
        "images": fallback.get("images", []),
        "models": fallback.get("models", []),
    }


def skin_media_summary(
    assets: dict[str, dict[str, Any]],
    rendered_skin: dict[str, Any] | None,
    weapon_id: str | int,
) -> dict[str, Any]:
    if rendered_skin is not None:
        preview_images = rendered_skin.get("preview_images", {})
        ordered_pngs = [
            preview_images[tier]
            for tier in ("light", "medium", "heavy")
            if tier in preview_images
        ]
        return {
            "asset_id": f"skin__{rendered_skin['entity_id']}",
            "manifest_path": rendered_skin["manifest_path"],
            "preview_status": rendered_skin.get("preview_status", "rendered"),
            "primary_image_png": rendered_skin.get("primary_preview_path"),
            "primary_preview_tier": rendered_skin.get("primary_preview_tier"),
            "images_png": ordered_pngs,
            "preview_images": preview_images,
            "source_texture_paths": rendered_skin.get("source_texture_paths", {}),
            "models": [],
        }

    fallback = media_summary(assets, "weapon", weapon_id, preview_status="weapon-base-fallback")
    return {
        **fallback,
        "primary_image_png": None,
        "primary_preview_tier": None,
        "images_png": [],
        "preview_images": {},
        "source_texture_paths": {},
    }


def skin_variant_media_summary(rendered_variant: dict[str, Any] | None) -> dict[str, Any]:
    if rendered_variant is None:
        return {
            "manifest_path": None,
            "preview_status": "unavailable",
            "image_png": None,
            "preview_tier": None,
            "source_skin_manifest_path": None,
        }
    return {
        "manifest_path": rendered_variant["manifest_path"],
        "preview_status": rendered_variant.get("preview_status", "shared-skin-render"),
        "image_png": rendered_variant.get("image_path"),
        "preview_tier": rendered_variant.get("preview_tier"),
        "source_skin_manifest_path": rendered_variant.get("source_skin_manifest_path"),
    }


def rendered_folder_name(entity_type: str) -> str | None:
    mapping = {
        "agent": "agents",
        "charm": "charms",
        "container": "containers",
        "graffiti": "graffiti",
        "music-kit": "music-kits",
        "patch": "patches",
        "sticker": "stickers",
        "tool": "tools",
        "weapon": "weapons",
    }
    return mapping.get(entity_type)


def localized_values(localizer: Localizer, token: str | None, fallback: str | None, locales: list[str]) -> dict[str, str]:
    values = {}
    for locale in locales:
        value = localizer.resolve(token, locale) if token else None
        if value:
            values[locale] = value
    if fallback and localizer.default_locale not in values:
        values[localizer.default_locale] = fallback
    return values


def combine_localized_maps(left: dict[str, str], right: dict[str, str], locales: list[str]) -> dict[str, str]:
    values = {}
    for locale in locales:
        left_value = left.get(locale) or left.get("english")
        right_value = right.get(locale) or right.get("english")
        if left_value and right_value:
            values[locale] = f"{left_value} | {right_value}"
    if "english" not in values and left.get("english") and right.get("english"):
        values["english"] = f"{left['english']} | {right['english']}"
    return values


def card_ref(group_name: str, entity_id: str | int, name: str, search_slug: str | None, card_type: str) -> dict[str, Any]:
    return {
        "id": str(entity_id),
        "name": name,
        "card_type": card_type,
        "group": group_name,
        "search_slug": search_slug,
        "path": f"data/api/consumer/cards/{group_name}/{entity_id}.json",
    }


def classify_glove_pool(paint_kit: dict[str, Any]) -> str | None:
    resolved = paint_kit.get("resolved", {})
    if resolved.get("composite_material_path"):
        return "volatile-gloves"
    paint_kit_id = int(paint_kit["id"])
    if 10006 <= paint_kit_id <= 10038:
        return "legacy-gloves"
    if 10039 <= paint_kit_id <= 10064:
        return "hydra-era-gloves"
    if 10065 <= paint_kit_id <= 10088:
        return "broken-fang-gloves"
    return None


def classify_glove_family(paint_kit: dict[str, Any]) -> str | None:
    name = str(paint_kit.get("name") or "")
    if name.startswith("glove_driver_") or name.startswith("slick_"):
        return "slick"
    if name.startswith("glove_sport_") or name.startswith("sporty_"):
        return "sporty"
    if name.startswith("glove_specialist_") or name.startswith("specialist_"):
        return "specialist"
    if name.startswith("handwrap_"):
        return "handwrap"
    if name.startswith("motorcycle_"):
        return "motorcycle"
    if name.startswith("bloodhound_hydra_"):
        return "hydra"
    if name.startswith("bloodhound_"):
        return "bloodhound"
    if name.startswith("operation10_"):
        return "brokenfang"
    return None


def first_nonempty(values: list[str] | None) -> str | None:
    if not values:
        return None
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
    return None
