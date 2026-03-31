from __future__ import annotations

from collections import defaultdict
from typing import Any

from cs2_skins_api.normalize import Localizer
from cs2_skins_api.special_pools import (
    build_special_pool_candidate_specs,
    special_pool_category,
    special_pool_expansion_status,
)
from cs2_skins_api.trading import (
    FINISH_FAMILY_SPECS,
    MARKET_CONSTRAINT_SPECS,
    RARE_PATTERN_SPECS,
    csfloat_category,
    finish_family_id,
    finish_family_spec,
    is_placeholder_name,
    pattern_sensitivity,
    phase_metadata,
    rare_pattern_mechanics,
    source_market_flags,
    support_flags,
    variant_float_window,
)
from cs2_skins_api.utils import build_canonical_slug, encode_path_key, slugify, unique_list


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
    finish_taxonomy = build_finish_taxonomy(api["finishes"])
    market_flags = build_market_flag_map(core.get("resolved_items", {}))

    special_pool_cards = build_special_pool_cards(core, api, localizer, locales, finish_name_map, weapon_name_map)
    weapon_cards = build_weapon_cards(
        api["weapons"],
        api["assets"],
        api["relations"],
        special_pool_cards,
        rendered,
        market_flags,
        localizer,
        locales,
    )
    skin_cards = build_skin_cards(
        api["skins"],
        api["weapons"],
        api["finishes"],
        api["special_drops"],
        api["containers"],
        api["assets"],
        rendered,
        localizer,
        locales,
        finish_name_map,
        weapon_name_map,
        finish_taxonomy,
    )
    variant_cards = build_variant_cards(api["skin_variants"], skin_cards, rendered, finish_taxonomy)
    container_cards = build_container_cards(
        api["containers"],
        api["assets"],
        api["relations"],
        api["weapons"],
        api["finishes"],
        skin_cards,
        special_pool_cards,
        rendered,
        market_flags,
        localizer,
        locales,
        rarity_labels,
    )
    collection_cards = build_collection_cards(api["collections"], api["relations"], api["assets"], localizer, locales)
    collectible_cards = build_simple_cards(api["collectibles"], api["assets"], rendered, "collectible", market_flags, localizer, locales)
    equipment_cards = build_simple_cards(api["equipment"], api["assets"], rendered, "equipment", market_flags, localizer, locales)
    sticker_cards = build_decal_cards(api["stickers"], api["assets"], rendered, "sticker", localizer, locales)
    patch_cards = build_decal_cards(api["patches"], api["assets"], rendered, "patch", localizer, locales)
    graffiti_cards = build_decal_cards(api["graffiti"], api["assets"], rendered, "graffiti", localizer, locales)
    agent_cards = build_agent_cards(api["agents"], api["assets"], rendered, market_flags, localizer, locales)
    charm_cards = build_simple_cards(api["charms"], api["assets"], rendered, "charm", market_flags, localizer, locales)
    music_kit_cards = build_simple_cards(api["music_kits"], api["assets"], rendered, "music-kit", market_flags, localizer, locales)
    tool_cards = build_simple_cards(api["tools"], api["assets"], rendered, "tool", market_flags, localizer, locales)
    tournament_cards = build_event_cards(api["tournaments"], api["relations"], localizer, locales)
    team_cards = build_team_cards(api["teams"], api["relations"], localizer, locales)
    player_cards = build_player_cards(api["players"], api["relations"])

    cards = {
        "weapons": weapon_cards,
        "skins": skin_cards,
        "skin-variants": variant_cards,
        **container_cards,
        "collections": collection_cards,
        "collectibles": collectible_cards,
        "equipment": equipment_cards,
        "stickers": sticker_cards,
        "patches": patch_cards,
        "graffiti": graffiti_cards,
        "special-pools": special_pool_cards,
        "agents": agent_cards,
        "charms": charm_cards,
        "music-kits": music_kit_cards,
        "tools": tool_cards,
        "tournaments": tournament_cards,
        "teams": team_cards,
        "players": player_cards,
    }

    overlays = build_consumer_overlays(cards, api["finishes"], finish_taxonomy)
    lists = build_consumer_lists(cards, overlays)
    browse = build_consumer_browse(cards, overlays)
    discovery = build_consumer_discovery(cards, overlays, lists)
    facets = build_consumer_facets(cards, overlays, special_pool_cards)
    stats = {
        card_group: len(group_cards)
        for card_group, group_cards in cards.items()
    }
    stats.update({
        f"overlays.{overlay_group}": len(group_payload)
        for overlay_group, group_payload in overlays.items()
    })

    return {
        "cards": cards,
        "lists": lists,
        "browse": browse,
        "overlays": overlays,
        "meta": {
            "discovery": discovery,
            "facets": facets,
        },
        "stats": stats,
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
        candidate_specs = build_special_pool_candidate_specs(token, paint_kits, api["weapons"])
        exact_candidates = [
            build_candidate_item(
                weapon_id=spec["weapon_id"],
                paint_kit=paint_kits[str(spec["paint_kit_id"])],
                weapons=api["weapons"],
                weapon_name_map=weapon_name_map,
                finish_name_map=finish_name_map,
                localizer=localizer,
                locales=locales,
                source_pool_id=token,
                item_category=spec["category"],
                expansion_rule=spec["expansion_rule"],
            )
            for spec in candidate_specs
            if str(spec["paint_kit_id"]) in paint_kits
        ]
        pool_category = special_pool_category(token)
        expansion_status = special_pool_expansion_status(token, paint_kits, api["weapons"])
        eligible_weapon_ids = unique_list(
            [
                candidate["weapon"]["id"]
                for candidate in exact_candidates
                if candidate.get("weapon", {}).get("id") is not None
            ]
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
            "canonical_slug": build_canonical_slug(token, token),
            "search_slug": pool.get("search_slug") or slugify(pool["name"]),
            "source_cases": [
                card_ref(
                    "cases",
                    container_id,
                    api["containers"][container_id]["name"],
                    api["containers"][container_id].get("canonical_slug"),
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
                    api["containers"][container_id].get("canonical_slug"),
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
                    "canonical_slug": api["weapons"][str(weapon_id)]["canonical_slug"],
                    "search_slug": api["weapons"][str(weapon_id)]["search_slug"],
                }
                for weapon_id in eligible_weapon_ids
                if str(weapon_id) in api["weapons"]
            ],
            "finish_profiles": [],
            "candidate_items": exact_candidates,
        }
    return special_pools

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
    expansion_rule: str | None = None,
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
        "canonical_slug": build_canonical_slug(None, f"{weapon_id}-{paint_kit['id']}"),
        "search_slug": slugify(f"{weapon['name']} {paint_kit['display_name'] or paint_kit['name']}"),
        "source_pool_id": source_pool_id,
        "weapon": {
            "id": weapon_id,
            "name": weapon["name"],
            "weapon_group": weapon["weapon_group"],
            "canonical_slug": weapon["canonical_slug"],
            "search_slug": weapon["search_slug"],
        },
        "finish": {
            "id": paint_kit["id"],
            "name": paint_kit["display_name"] or paint_kit["name"],
            "style_code": finish_style_code,
            "style_name": FINISH_STYLE_LABELS.get(finish_style_code),
            "rarity_ref": paint_kit.get("rarity_ref"),
            "canonical_slug": build_canonical_slug(paint_kit.get("name"), paint_kit["id"]),
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
            "expansion_rule": expansion_rule,
        },
    }


def build_market_flag_map(resolved_items: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(item_id): source_market_flags(record)
        for item_id, record in resolved_items.items()
    }


def build_finish_taxonomy(finishes: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    family_by_finish: dict[str, dict[str, Any]] = {}
    phase_by_finish: dict[str, dict[str, Any]] = {}
    for finish_id, finish in finishes.items():
        family_id = finish_family_id(finish)
        family_by_finish[str(finish_id)] = {
            "family_id": family_id,
            "family_spec": finish_family_spec(family_id),
            "mechanics": rare_pattern_mechanics(family_id),
            "support_flags": support_flags(family_id),
        }
        phase = phase_metadata(finish, family_id)
        if phase is not None:
            phase_by_finish[str(finish_id)] = phase
    return {
        "family_by_finish": family_by_finish,
        "phase_by_finish": phase_by_finish,
    }


def build_weapon_cards(
    weapons: dict[str, dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    relations: dict[str, Any],
    special_pools: dict[str, dict[str, Any]],
    rendered: dict[str, Any],
    market_flags: dict[str, dict[str, Any]],
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
            "canonical_slug": weapon["canonical_slug"],
            "search_slug": weapon["search_slug"],
            "weapon_group": group,
            "side": weapon.get("side"),
            "type_name": weapon.get("type_name"),
            "description": weapon.get("description"),
            "media": generic_rendered_media_summary(rendered, "weapon", weapon_id, media_summary(assets, "weapon", weapon_id)),
            "market": build_source_market_summary(market_flags.get(str(weapon_id))),
            "supports_vanilla": group == "knife",
            "regular_skin_ids": sorted(set(skins_by_weapon.get(weapon_id, []))),
            "special_pool_ids": sorted(set(special_pool_ids_by_weapon.get(weapon_id, []))),
        }
    return cards


def build_skin_cards(
    skins: dict[str, dict[str, Any]],
    weapons: dict[str, dict[str, Any]],
    finishes: dict[str, dict[str, Any]],
    special_drops: dict[str, dict[str, Any]],
    containers: dict[str, dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    rendered: dict[str, Any],
    localizer: Localizer,
    locales: list[str],
    finish_name_map: dict[str, dict[str, str]],
    weapon_name_map: dict[str, dict[str, str]],
    finish_taxonomy: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    cards = {}
    for skin_id, skin in skins.items():
        weapon_id = str(skin["weapon"]["id"])
        finish_id = str(skin["finish"]["id"])
        finish = finishes[finish_id]
        weapon = weapons[weapon_id]
        finish_style_code = finish.get("style_code")
        rendered_skin = rendered.get("skins", {}).get(skin_id)
        card_type = "weapon-skin"
        if weapon["weapon_group"] == "knife":
            card_type = "knife"
        elif weapon["weapon_group"] == "glove":
            card_type = "glove"
        cards[skin_id] = {
            "id": skin_id,
            "card_type": card_type,
            "name": skin["name"],
            "localized_names": combine_localized_maps(
                weapon_name_map.get(weapon_id, {}),
                finish_name_map.get(finish_id, {}),
                locales,
            ),
            "canonical_slug": skin["canonical_slug"],
            "search_slug": skin["search_slug"],
            "weapon": {
                "id": weapon["id"],
                "name": weapon["name"],
                "localized_names": weapon_name_map.get(weapon_id, {}),
                "weapon_group": weapon["weapon_group"],
                "canonical_slug": weapon["canonical_slug"],
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
                "canonical_slug": finish["canonical_slug"],
            },
            "wear": skin["wear"],
            "available_exteriors": skin.get("supported_exteriors", []),
            "availability": skin.get("availability", {}),
            "generation_notes": skin.get("generation_notes", {}),
            "sources": build_skin_sources(skin, special_drops, containers),
            "variant_ids": sorted(skin.get("variant_ids", [])),
            "media": skin_media_summary(assets, rendered, rendered_skin, weapon_id),
            "trading": build_skin_trading_profile(
                skin_id=skin_id,
                skin=skin,
                finish=finish,
                card_type=card_type,
                finish_taxonomy=finish_taxonomy,
            ),
        }
    return cards


def build_variant_cards(
    variants: dict[str, dict[str, Any]],
    skin_cards: dict[str, dict[str, Any]],
    rendered: dict[str, Any],
    finish_taxonomy: dict[str, dict[str, Any]],
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
            "canonical_slug": variant["canonical_slug"],
            "search_slug": variant["search_slug"],
            "market_hash_name": variant["market_hash_name"],
            "quality": variant["quality"],
            "quality_name": variant["quality_name"],
            "exterior": variant["exterior"],
            "exterior_name": variant["exterior_name"],
            "skin_name": skin["name"] if skin else None,
            "media": skin_variant_media_summary(rendered_variant, skin.get("media") if skin else None),
            "trading": build_variant_trading_profile(
                variant=variant,
                skin_card=skin,
                finish_taxonomy=finish_taxonomy,
            ),
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
    market_flags: dict[str, dict[str, Any]],
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
                    item = card_ref("skins", skin_id, name, build_canonical_slug(None, skin_id), slugify(name), "weapon-skin")
                else:
                    item = card_ref("skins", skin_id, skin_card["name"], skin_card.get("canonical_slug"), skin_card["search_slug"], skin_card["card_type"])
                if drop.get("tier"):
                    by_rarity[drop["tier"]].append(item)
                drop_summaries.append({**item, "tier": drop.get("tier")})
            elif drop["kind"] == "special-drop":
                pool = special_pools.get(drop["special_drop_id"])
                if pool:
                    item = card_ref("special-pools", pool["id"], pool["name"], pool.get("canonical_slug"), pool["search_slug"], pool["card_type"])
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
            "canonical_slug": container["canonical_slug"],
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
            "market": build_source_market_summary(market_flags.get(str(container_id))),
            "skin_ids": sorted(relations.get("container-to-skins", {}).get(container_id, [])),
            "special_pools": sorted(special_pool_refs, key=lambda row: row["name"]),
            "trading": build_container_trading_summary(
                relations.get("container-to-skins", {}).get(container_id, []),
                skin_cards,
                special_pool_refs,
            ),
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
            "canonical_slug": collection["canonical_slug"],
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
            "canonical_slug": entity["canonical_slug"],
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
    market_flags: dict[str, dict[str, Any]],
    localizer: Localizer,
    locales: list[str],
) -> dict[str, dict[str, Any]]:
    cards = {}
    for entity_id, entity in entities.items():
        card = {
            "id": entity["id"],
            "card_type": card_type,
            "name": entity["name"],
            "localized_names": localized_values(localizer, entity.get("name_token"), entity["name"], locales),
            "canonical_slug": entity["canonical_slug"],
            "search_slug": entity["search_slug"],
            "description": entity.get("description"),
            "media": generic_rendered_media_summary(rendered, card_type, entity_id, media_summary(assets, card_type, entity_id)),
            "market": build_source_market_summary(market_flags.get(str(entity_id))),
        }
        for key in (
            "campaign_id",
            "collectible_group",
            "equipment_group",
            "rarity_ref",
            "side",
            "tool_type",
            "tournament_event_id",
            "upgrade_level",
        ):
            if entity.get(key) is not None:
                card[key] = entity.get(key)
        cards[entity_id] = card
    return cards


def build_agent_cards(
    agents: dict[str, dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    rendered: dict[str, Any],
    market_flags: dict[str, dict[str, Any]],
    localizer: Localizer,
    locales: list[str],
) -> dict[str, dict[str, Any]]:
    cards = {}
    for entity_id, entity in agents.items():
        cards[entity_id] = {
            "id": entity["id"],
            "card_type": "agent",
            "name": entity["name"],
            "localized_names": localized_values(localizer, None, entity["name"], locales),
            "canonical_slug": entity["canonical_slug"],
            "search_slug": entity["search_slug"],
            "description": entity.get("description"),
            "side": entity.get("side"),
            "rarity_ref": entity.get("rarity_ref"),
            "media": generic_rendered_media_summary(rendered, "agent", entity_id, media_summary(assets, "agent", entity_id)),
            "market": build_source_market_summary(market_flags.get(str(entity_id))),
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
            "canonical_slug": tournament["canonical_slug"],
            "search_slug": tournament["search_slug"],
            "year": tournament.get("year"),
            "team_ids": sorted(relations.get("tournament-to-teams", {}).get(tournament_id, [])),
            "player_ids": sorted(relations.get("tournament-to-players", {}).get(tournament_id, [])),
            "container_ids": sorted(relations.get("tournament-to-containers", {}).get(tournament_id, [])),
            "collectible_ids": sorted(relations.get("tournament-to-collectibles", {}).get(tournament_id, [])),
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
            "canonical_slug": team["canonical_slug"],
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
            "canonical_slug": player["canonical_slug"],
            "search_slug": player["search_slug"],
            "code": player.get("code"),
            "country_code": player.get("country_code"),
            "team_ids": sorted(relations.get("player-to-teams", {}).get(player_id, [])),
            "tournament_ids": sorted(relations.get("player-to-tournaments", {}).get(player_id, [])),
        }
    return cards


def build_skin_sources(
    skin: dict[str, Any],
    special_drops: dict[str, dict[str, Any]],
    containers: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    cases = []
    capsules = []
    souvenir_packages = []
    other_containers = []
    special_pools = []
    for container in skin.get("sources", {}).get("containers", []):
        ref = {
            "id": container["id"],
            "name": container["name"],
            "kind": container["kind"],
            "tier": container.get("tier"),
            "flags": container.get("flags", []),
            "canonical_slug": container.get("canonical_slug"),
            "search_slug": container.get("search_slug"),
        }
        if container["kind"] == "weapon-case":
            cases.append(ref)
        elif container["kind"] == "souvenir-package":
            souvenir_packages.append(ref)
        elif container["kind"] == "sticker-capsule":
            capsules.append(ref)
        else:
            other_containers.append(ref)
    for special_pool in skin.get("sources", {}).get("special_pools", []):
        pool_ref = {
            "id": special_pool["id"],
            "name": special_pool["name"],
            "kind": special_pool["kind"],
            "canonical_slug": special_pool.get("canonical_slug"),
            "search_slug": special_pool.get("search_slug"),
            "source_backed": special_pool.get("source_backed", False),
            "expansion_rule": special_pool.get("expansion_rule"),
        }
        special_pools.append(pool_ref)
        pool = special_drops.get(str(special_pool["id"])) or special_drops.get(special_pool["id"])
        source_container_ids = pool.get("source_container_ids", []) if pool else []
        for container_id in source_container_ids:
            source_container = containers.get(str(container_id)) or containers.get(container_id)
            if source_container is None:
                continue
            ref = {
                "id": source_container["id"],
                "name": source_container["name"],
                "kind": source_container["container_kind"],
                "canonical_slug": source_container.get("canonical_slug"),
                "search_slug": source_container.get("search_slug"),
                "via_special_pool": special_pool["id"],
            }
            if source_container["container_kind"] == "weapon-case":
                cases.append(ref)
            elif source_container["container_kind"] == "souvenir-package":
                souvenir_packages.append(ref)
            elif source_container["container_kind"] == "sticker-capsule":
                capsules.append(ref)
            else:
                other_containers.append(ref)
    return {
        "collections": skin.get("sources", {}).get("collections", []),
        "cases": unique_list(cases),
        "capsules": unique_list(capsules),
        "souvenir_packages": unique_list(souvenir_packages),
        "containers": unique_list(other_containers),
        "special_pools": unique_list(special_pools),
    }


def overlay_ref(group_name: str, entity_id: str | int, name: str, canonical_slug: str | None = None, search_slug: str | None = None) -> dict[str, Any]:
    return {
        "id": str(entity_id),
        "name": name,
        "group": group_name,
        "canonical_slug": canonical_slug,
        "search_slug": search_slug,
        "path": f"data/api/consumer/overlays/{group_name}/{entity_id}.json",
    }


def reference_ref(
    group_name: str,
    entity_id: str | int,
    name: str,
    canonical_slug: str | None = None,
    search_slug: str | None = None,
) -> dict[str, Any]:
    return {
        "id": str(entity_id),
        "name": name,
        "group": group_name,
        "canonical_slug": canonical_slug,
        "search_slug": search_slug,
        "path": f"data/api/reference/{group_name}/{entity_id}.json",
    }


def build_source_market_summary(flags: dict[str, Any] | None) -> dict[str, Any]:
    flags = flags or {"trade_state": "not-explicit", "cannot_trade": False}
    constraints = []
    if flags.get("cannot_trade"):
        spec = MARKET_CONSTRAINT_SPECS["cannot-trade"]
        constraints.append(
            overlay_ref(
                "market-constraints",
                "cannot-trade",
                spec["name"],
                build_canonical_slug("cannot-trade"),
                slugify(spec["name"]),
            )
        )
    return {
        "trade_state": flags.get("trade_state", "not-explicit"),
        "market_constraints": constraints,
    }


def build_skin_trading_profile(
    skin_id: str,
    skin: dict[str, Any],
    finish: dict[str, Any],
    card_type: str,
    finish_taxonomy: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    finish_meta = finish_taxonomy["family_by_finish"].get(str(finish["id"]), {})
    family_id = finish_meta.get("family_id")
    family_spec = finish_meta.get("family_spec")
    support_meta = finish_meta.get("support_flags", support_flags(family_id))
    mechanics = finish_meta.get("mechanics", [])
    phase = finish_taxonomy["phase_by_finish"].get(str(finish["id"]))
    finish_family = None
    if family_id and family_spec:
        finish_family = overlay_ref(
            "finish-families",
            family_id,
            family_spec["name"],
            build_canonical_slug(family_id),
            slugify(family_spec["name"]),
        )
    phase_ref = None
    if phase:
        phase_ref = overlay_ref(
            "phases",
            phase["id"],
            phase["name"],
            phase.get("canonical_slug"),
            phase.get("search_slug"),
        )
    mechanic_refs = [
        overlay_ref(
            "rare-patterns",
            mechanic_id,
            RARE_PATTERN_SPECS[mechanic_id]["name"],
            build_canonical_slug(mechanic_id),
            slugify(RARE_PATTERN_SPECS[mechanic_id]["name"]),
        )
        for mechanic_id in mechanics
        if mechanic_id in RARE_PATTERN_SPECS
    ]
    live_market_constraint = overlay_ref(
        "market-constraints",
        "live-item-market-state",
        MARKET_CONSTRAINT_SPECS["live-item-market-state"]["name"],
        build_canonical_slug("live-item-market-state"),
        slugify(MARKET_CONSTRAINT_SPECS["live-item-market-state"]["name"]),
    )
    return {
        "consumer_type": card_type,
        "finish_family": finish_family,
        "pattern_sensitive": bool(mechanics),
        "pattern_sensitivity": pattern_sensitivity(family_id),
        "pattern_mechanics": mechanic_refs,
        "phase": phase_ref,
        "supports": support_meta,
        "float_window": {
            "min_float": skin["wear"].get("min_float"),
            "max_float": skin["wear"].get("max_float"),
        },
        "inspect_ref": {
            "def_index": skin["weapon"]["id"],
            "paint_index": finish["id"],
            "paint_seed_field": "paint_seed" if mechanics else None,
            "live_item_required": True,
        },
        "market_query": {
            "skin_name": skin["name"],
            "variant_ids": sorted(skin.get("variant_ids", [])),
            "csfloat": {
                "def_index": skin["weapon"]["id"],
                "paint_index": finish["id"],
                "supports_paint_seed_filter": bool(mechanics),
            },
        },
        "market_constraints": [live_market_constraint],
    }


def build_variant_trading_profile(
    variant: dict[str, Any],
    skin_card: dict[str, Any] | None,
    finish_taxonomy: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if skin_card is None:
        return {
            "market_query": {
                "market_hash_name": variant["market_hash_name"],
                "consumer_list_path": f"data/api/consumer/lists/by-market-hash-name/{encode_path_key(variant['market_hash_name'])}.json",
                "graph_index_path": f"data/api/graph/indexes/by-market-hash-name/{encode_path_key(variant['market_hash_name'])}.json",
            }
        }
    finish_id = str(skin_card["finish"]["id"])
    finish_meta = finish_taxonomy["family_by_finish"].get(finish_id, {})
    family_id = finish_meta.get("family_id")
    family_spec = finish_meta.get("family_spec")
    support_meta = finish_meta.get("support_flags", support_flags(family_id))
    mechanics = finish_meta.get("mechanics", [])
    phase = finish_taxonomy["phase_by_finish"].get(finish_id)
    finish_family = None
    if family_id and family_spec:
        finish_family = overlay_ref(
            "finish-families",
            family_id,
            family_spec["name"],
            build_canonical_slug(family_id),
            slugify(family_spec["name"]),
        )
    phase_ref = None
    if phase:
        phase_ref = overlay_ref(
            "phases",
            phase["id"],
            phase["name"],
            phase.get("canonical_slug"),
            phase.get("search_slug"),
        )
    mechanic_refs = [
        overlay_ref(
            "rare-patterns",
            mechanic_id,
            RARE_PATTERN_SPECS[mechanic_id]["name"],
            build_canonical_slug(mechanic_id),
            slugify(RARE_PATTERN_SPECS[mechanic_id]["name"]),
        )
        for mechanic_id in mechanics
        if mechanic_id in RARE_PATTERN_SPECS
    ]
    exterior = next(
        (
            option
            for option in skin_card.get("available_exteriors", [])
            if option.get("id") == variant["exterior"]
        ),
        {"id": variant["exterior"], "name": variant["exterior_name"]},
    )
    float_window = variant_float_window(skin_card.get("wear", {}), exterior)
    csfloat_payload = {
        "def_index": skin_card["weapon"]["id"],
        "paint_index": skin_card["finish"]["id"],
        "market_hash_name": variant["market_hash_name"],
        "category": {
            "id": variant["quality"],
            "code": csfloat_category(variant["quality"]),
        },
        "supports_paint_seed_filter": bool(mechanics),
    }
    if float_window is not None:
        csfloat_payload["min_float"] = float_window["min_float"]
        csfloat_payload["max_float"] = float_window["max_float"]
    live_market_constraint = overlay_ref(
        "market-constraints",
        "live-item-market-state",
        MARKET_CONSTRAINT_SPECS["live-item-market-state"]["name"],
        build_canonical_slug("live-item-market-state"),
        slugify(MARKET_CONSTRAINT_SPECS["live-item-market-state"]["name"]),
    )
    return {
        "finish_family": finish_family,
        "pattern_sensitive": bool(mechanics),
        "pattern_sensitivity": pattern_sensitivity(family_id),
        "pattern_mechanics": mechanic_refs,
        "phase": phase_ref,
        "supports": support_meta,
        "variant_float_window": float_window,
        "inspect_ref": {
            "def_index": skin_card["weapon"]["id"],
            "paint_index": skin_card["finish"]["id"],
            "quality": variant["quality"],
            "paint_seed_field": "paint_seed" if mechanics else None,
            "live_item_required_fields": ["asset_id", "d_param"],
        },
        "market_query": {
            "market_hash_name": variant["market_hash_name"],
            "consumer_list_path": f"data/api/consumer/lists/by-market-hash-name/{encode_path_key(variant['market_hash_name'])}.json",
            "graph_index_path": f"data/api/graph/indexes/by-market-hash-name/{encode_path_key(variant['market_hash_name'])}.json",
            "csfloat": csfloat_payload,
        },
        "market_constraints": [live_market_constraint],
    }


def build_container_trading_summary(
    skin_ids: list[str],
    skin_cards: dict[str, dict[str, Any]],
    special_pool_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    finish_families = []
    pattern_mechanics = []
    contains_weapon_groups: set[str] = set()
    for skin_id in skin_ids:
        skin_card = skin_cards.get(skin_id)
        if skin_card is None:
            continue
        contains_weapon_groups.add(str(skin_card.get("weapon", {}).get("weapon_group")))
        trading = skin_card.get("trading", {})
        finish_family = trading.get("finish_family")
        if finish_family:
            finish_families.append(finish_family)
        pattern_mechanics.extend(trading.get("pattern_mechanics", []))
    return {
        "contains_weapon_groups": sorted(group for group in contains_weapon_groups if group),
        "rare_special_item_count": len(special_pool_refs),
        "finish_families": unique_list(sorted(finish_families, key=lambda row: row["name"])),
        "pattern_mechanics": unique_list(sorted(pattern_mechanics, key=lambda row: row["name"])),
    }


def build_consumer_overlays(
    cards: dict[str, dict[str, dict[str, Any]]],
    finishes: dict[str, dict[str, Any]],
    finish_taxonomy: dict[str, dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    skin_refs_by_finish: dict[str, list[dict[str, Any]]] = defaultdict(list)
    skin_refs_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    variant_refs_by_finish: dict[str, list[dict[str, Any]]] = defaultdict(list)
    variant_refs_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    family_finish_ids: dict[str, set[str]] = defaultdict(set)
    family_weapon_groups: dict[str, set[str]] = defaultdict(set)
    mechanic_skin_refs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    mechanic_variant_refs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    mechanic_family_ids: dict[str, set[str]] = defaultdict(set)
    constraint_refs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    constraint_group_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    skins = cards.get("skins", {})
    variants = cards.get("skin-variants", {})

    for skin_id, card in skins.items():
        ref = card_ref("skins", skin_id, card["name"], card.get("canonical_slug"), card["search_slug"], card["card_type"])
        finish_id = str(card["finish"]["id"])
        skin_refs_by_finish[finish_id].append(ref)
        trading = card.get("trading", {})
        family = trading.get("finish_family")
        if family:
            family_id = family["id"]
            skin_refs_by_family[family_id].append(ref)
            family_finish_ids[family_id].add(finish_id)
            weapon_group = card.get("weapon", {}).get("weapon_group")
            if weapon_group:
                family_weapon_groups[family_id].add(weapon_group)
        for mechanic in trading.get("pattern_mechanics", []):
            mechanic_id = mechanic["id"]
            mechanic_skin_refs[mechanic_id].append(ref)
            if family:
                mechanic_family_ids[mechanic_id].add(family["id"])
        for constraint in trading.get("market_constraints", []):
            constraint_id = constraint["id"]
            constraint_refs[constraint_id].append(ref)
            constraint_group_counts[constraint_id]["skins"] += 1

    for variant_id, card in variants.items():
        ref = card_ref(
            "skin-variants",
            variant_id,
            card["name"],
            card.get("canonical_slug"),
            card["search_slug"],
            card["card_type"],
        )
        skin = skins.get(card["skin_id"])
        if skin is not None:
            finish_id = str(skin["finish"]["id"])
            variant_refs_by_finish[finish_id].append(ref)
        trading = card.get("trading", {})
        family = trading.get("finish_family")
        if family:
            variant_refs_by_family[family["id"]].append(ref)
        for mechanic in trading.get("pattern_mechanics", []):
            mechanic_id = mechanic["id"]
            mechanic_variant_refs[mechanic_id].append(ref)
            if family:
                mechanic_family_ids[mechanic_id].add(family["id"])
        for constraint in trading.get("market_constraints", []):
            constraint_id = constraint["id"]
            constraint_refs[constraint_id].append(ref)
            constraint_group_counts[constraint_id]["skin-variants"] += 1

    for group_name, group_cards in cards.items():
        for card_id, card in group_cards.items():
            market = card.get("market", {})
            for constraint in market.get("market_constraints", []):
                constraint_id = constraint["id"]
                ref = card_ref(
                    group_name,
                    card_id,
                    card.get("name") or str(card_id),
                    card.get("canonical_slug"),
                    card.get("search_slug"),
                    card["card_type"],
                )
                constraint_refs[constraint_id].append(ref)
                constraint_group_counts[constraint_id][group_name] += 1

    overlays: dict[str, dict[str, dict[str, Any]]] = {
        "finish-families": {},
        "rare-patterns": {},
        "phases": {},
        "market-constraints": {},
    }

    for family_id, spec in sorted(FINISH_FAMILY_SPECS.items()):
        finish_ids = sorted(family_finish_ids.get(family_id, set()), key=lambda value: int(value))
        finish_refs = [
            reference_ref(
                "finishes",
                finish_id,
                finishes[finish_id]["name"],
                finishes[finish_id].get("canonical_slug"),
                finishes[finish_id].get("search_slug"),
            )
            for finish_id in finish_ids
            if finish_id in finishes
        ]
        skin_refs = unique_list(sorted(skin_refs_by_family.get(family_id, []), key=lambda row: row["name"]))
        variant_refs = unique_list(sorted(variant_refs_by_family.get(family_id, []), key=lambda row: row["name"]))
        overlays["finish-families"][family_id] = {
            "id": family_id,
            "overlay_type": "finish-family",
            "name": spec["name"],
            "description": spec["description"],
            "canonical_slug": build_canonical_slug(family_id),
            "search_slug": slugify(spec["name"]),
            "knowledge_source": spec.get("knowledge_source"),
            "confidence": spec.get("confidence"),
            "pattern_sensitive": spec.get("pattern_sensitive", False),
            "pattern_sensitivity": spec.get("pattern_sensitivity", "none"),
            "primary_mechanics": [
                overlay_ref(
                    "rare-patterns",
                    mechanic_id,
                    RARE_PATTERN_SPECS[mechanic_id]["name"],
                    build_canonical_slug(mechanic_id),
                    slugify(RARE_PATTERN_SPECS[mechanic_id]["name"]),
                )
                for mechanic_id in spec.get("primary_mechanics", [])
                if mechanic_id in RARE_PATTERN_SPECS
            ],
            "supports": dict(spec.get("supports", {})),
            "finish_count": len(finish_refs),
            "skin_count": len(skin_refs),
            "variant_count": len(variant_refs),
            "weapon_groups": sorted(family_weapon_groups.get(family_id, set())),
            "finishes": finish_refs,
            "example_skins": skin_refs[:12],
            "list_paths": {
                "items": f"data/api/consumer/lists/by-finish-family/{encode_path_key(family_id)}.json",
            },
        }

    for mechanic_id, spec in sorted(RARE_PATTERN_SPECS.items()):
        family_ids = sorted(
            {
                family_id
                for family_id, family_spec in FINISH_FAMILY_SPECS.items()
                if mechanic_id in family_spec.get("primary_mechanics", [])
            }
            | mechanic_family_ids.get(mechanic_id, set())
        )
        finish_ids = sorted(
            {
                finish_id
                for family_id in family_ids
                for finish_id in family_finish_ids.get(family_id, set())
            },
            key=lambda value: int(value),
        )
        finish_refs = [
            reference_ref(
                "finishes",
                finish_id,
                finishes[finish_id]["name"],
                finishes[finish_id].get("canonical_slug"),
                finishes[finish_id].get("search_slug"),
            )
            for finish_id in finish_ids
            if finish_id in finishes
        ]
        overlays["rare-patterns"][mechanic_id] = {
            "id": mechanic_id,
            "overlay_type": "rare-pattern",
            "name": spec["name"],
            "description": spec["description"],
            "canonical_slug": build_canonical_slug(mechanic_id),
            "search_slug": slugify(spec["name"]),
            "knowledge_source": spec.get("knowledge_source"),
            "live_item_requirements": list(spec.get("live_item_requirements", [])),
            "finish_families": [
                overlay_ref(
                    "finish-families",
                    family_id,
                    FINISH_FAMILY_SPECS[family_id]["name"],
                    build_canonical_slug(family_id),
                    slugify(FINISH_FAMILY_SPECS[family_id]["name"]),
                )
                for family_id in family_ids
            ],
            "finish_count": len(finish_refs),
            "skin_count": len(unique_list(mechanic_skin_refs.get(mechanic_id, []))),
            "variant_count": len(unique_list(mechanic_variant_refs.get(mechanic_id, []))),
            "finishes": finish_refs,
            "example_skins": unique_list(sorted(mechanic_skin_refs.get(mechanic_id, []), key=lambda row: row["name"]))[:12],
            "list_paths": {
                "items": f"data/api/consumer/lists/by-pattern-mechanic/{encode_path_key(mechanic_id)}.json",
            },
        }

    for finish_id, phase in sorted(finish_taxonomy.get("phase_by_finish", {}).items(), key=lambda pair: pair[1]["name"]):
        finish = finishes.get(str(finish_id))
        family_id = phase.get("phase_group")
        family_spec = FINISH_FAMILY_SPECS.get(family_id) if family_id else None
        overlays["phases"][str(finish_id)] = {
            "id": str(finish_id),
            "overlay_type": "phase",
            "name": phase["name"],
            "canonical_slug": phase.get("canonical_slug"),
            "search_slug": phase.get("search_slug"),
            "phase_code": phase.get("phase_code"),
            "phase_name": phase.get("phase_name"),
            "phase_kind": phase.get("phase_kind"),
            "phase_group": phase.get("phase_group"),
            "finish_family": (
                overlay_ref(
                    "finish-families",
                    family_id,
                    family_spec["name"],
                    build_canonical_slug(family_id),
                    slugify(family_spec["name"]),
                )
                if family_id and family_spec
                else None
            ),
            "finish": (
                reference_ref(
                    "finishes",
                    finish_id,
                    finish["name"],
                    finish.get("canonical_slug"),
                    finish.get("search_slug"),
                )
                if finish is not None
                else None
            ),
            "pattern_mechanics": [
                overlay_ref(
                    "rare-patterns",
                    "phase",
                    RARE_PATTERN_SPECS["phase"]["name"],
                    build_canonical_slug("phase"),
                    slugify(RARE_PATTERN_SPECS["phase"]["name"]),
                )
            ],
            "skin_count": len(unique_list(skin_refs_by_finish.get(str(finish_id), []))),
            "variant_count": len(unique_list(variant_refs_by_finish.get(str(finish_id), []))),
            "example_skins": unique_list(sorted(skin_refs_by_finish.get(str(finish_id), []), key=lambda row: row["name"]))[:12],
            "list_paths": {
                "items": f"data/api/consumer/lists/by-finish/{encode_path_key(finish_id)}.json",
            },
        }

    for constraint_id, spec in sorted(MARKET_CONSTRAINT_SPECS.items()):
        affected_refs = unique_list(sorted(constraint_refs.get(constraint_id, []), key=lambda row: row["name"]))
        overlays["market-constraints"][constraint_id] = {
            "id": constraint_id,
            "overlay_type": "market-constraint",
            "name": spec["name"],
            "description": spec["description"],
            "canonical_slug": build_canonical_slug(constraint_id),
            "search_slug": slugify(spec["name"]),
            "knowledge_source": spec.get("knowledge_source"),
            "affected_item_count": len(affected_refs),
            "affected_groups": dict(sorted(constraint_group_counts.get(constraint_id, {}).items())),
            "sample_items": affected_refs[:24],
            "list_paths": {
                "items": f"data/api/consumer/lists/by-market-constraint/{encode_path_key(constraint_id)}.json",
            },
        }

    return overlays


def build_consumer_lists(cards: dict[str, dict[str, dict[str, Any]]], overlays: dict[str, dict[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    lists: dict[str, dict[str, Any]] = {
        "by-type": {},
        "by-weapon": defaultdict(list),
        "by-finish": defaultdict(list),
        "by-finish-family": defaultdict(list),
        "by-case": defaultdict(list),
        "by-collection": defaultdict(list),
        "by-exterior": defaultdict(list),
        "by-pattern-mechanic": defaultdict(list),
        "by-quality": defaultdict(list),
        "by-market-constraint": defaultdict(list),
        "by-side": defaultdict(list),
        "by-canonical-slug": defaultdict(list),
        "by-search-slug": defaultdict(list),
        "by-market-hash-name": defaultdict(list),
    }

    for group_name, group_cards in cards.items():
        refs = []
        for card_id, card in group_cards.items():
            ref = card_ref(
                group_name,
                card_id,
                card.get("name") or str(card_id),
                card.get("canonical_slug"),
                card.get("search_slug"),
                card["card_type"],
            )
            refs.append(ref)
            if card.get("canonical_slug"):
                lists["by-canonical-slug"][card["canonical_slug"]].append(ref)
            if card.get("search_slug"):
                lists["by-search-slug"][card["search_slug"]].append(ref)
            for constraint in card.get("market", {}).get("market_constraints", []):
                lists["by-market-constraint"][constraint["id"]].append(ref)
        lists["by-type"][group_name] = sorted(refs, key=lambda row: row["name"])

    for overlay_group, payload in overlays.items():
        for overlay_id, overlay in payload.items():
            ref = overlay_ref(
                overlay_group,
                overlay_id,
                overlay.get("name") or str(overlay_id),
                overlay.get("canonical_slug"),
                overlay.get("search_slug"),
            )
            if overlay.get("canonical_slug"):
                lists["by-canonical-slug"][overlay["canonical_slug"]].append(ref)
            if overlay.get("search_slug"):
                lists["by-search-slug"][overlay["search_slug"]].append(ref)

    for skin_id, card in cards.get("skins", {}).items():
        weapon_id = str(card["weapon"]["id"])
        finish_id = str(card["finish"]["id"])
        ref = card_ref("skins", skin_id, card["name"], card.get("canonical_slug"), card["search_slug"], card["card_type"])
        lists["by-weapon"][weapon_id].append(ref)
        lists["by-finish"][finish_id].append(ref)
        finish_family = card.get("trading", {}).get("finish_family")
        if finish_family:
            lists["by-finish-family"][finish_family["id"]].append(ref)
        for mechanic in card.get("trading", {}).get("pattern_mechanics", []):
            lists["by-pattern-mechanic"][mechanic["id"]].append(ref)
        for constraint in card.get("trading", {}).get("market_constraints", []):
            lists["by-market-constraint"][constraint["id"]].append(ref)
        for source in card.get("sources", {}).get("cases", []):
            lists["by-case"][str(source["id"])].append(ref)
        for source in card.get("sources", {}).get("collections", []):
            lists["by-collection"][str(source["id"])].append(ref)

    for variant_id, card in cards.get("skin-variants", {}).items():
        ref = card_ref("skin-variants", variant_id, card["name"], card.get("canonical_slug"), card["search_slug"], card["card_type"])
        lists["by-market-hash-name"][card["market_hash_name"]].append(ref)
        quality = card.get("quality")
        if quality:
            lists["by-quality"][quality].append(ref)
        exterior = card.get("exterior")
        if exterior:
            lists["by-exterior"][exterior].append(ref)
        finish_family = card.get("trading", {}).get("finish_family")
        if finish_family:
            lists["by-finish-family"][finish_family["id"]].append(ref)
        for mechanic in card.get("trading", {}).get("pattern_mechanics", []):
            lists["by-pattern-mechanic"][mechanic["id"]].append(ref)
        for constraint in card.get("trading", {}).get("market_constraints", []):
            lists["by-market-constraint"][constraint["id"]].append(ref)

    for agent_id, card in cards.get("agents", {}).items():
        side = card.get("side")
        if not side:
            continue
        lists["by-side"][side].append(
            card_ref("agents", agent_id, card["name"], card.get("canonical_slug"), card["search_slug"], card["card_type"])
        )

    return {
        list_name: normalize_list_payload(payload)
        for list_name, payload in lists.items()
    }


def build_consumer_browse(
    cards: dict[str, dict[str, dict[str, Any]]],
    overlays: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    def refs(group_name: str) -> list[dict[str, Any]]:
        group_cards = cards.get(group_name, {})
        return sorted(
            [
                card_ref(
                    group_name,
                    card_id,
                    card.get("name") or str(card_id),
                    card.get("canonical_slug"),
                    card.get("search_slug"),
                    card["card_type"],
                )
                for card_id, card in group_cards.items()
            ],
            key=lambda row: row["name"],
        )

    def filtered_refs(group_name: str, *, card_type: str | None = None, weapon_group: str | None = None) -> list[dict[str, Any]]:
        group_cards = cards.get(group_name, {})
        items = []
        for card_id, card in group_cards.items():
            if card_type and card.get("card_type") != card_type:
                continue
            if weapon_group and card.get("weapon_group") != weapon_group:
                continue
            items.append(
                card_ref(
                    group_name,
                    card_id,
                    card.get("name") or str(card_id),
                    card.get("canonical_slug"),
                    card.get("search_slug"),
                    card["card_type"],
                )
            )
        return sorted(items, key=lambda row: row["name"])

    def overlay_refs(group_name: str) -> list[dict[str, Any]]:
        payload = overlays.get(group_name, {})
        return sorted(
            [
                overlay_ref(
                    group_name,
                    overlay_id,
                    overlay.get("name") or str(overlay_id),
                    overlay.get("canonical_slug"),
                    overlay.get("search_slug"),
                )
                for overlay_id, overlay in payload.items()
            ],
            key=lambda row: row["name"],
        )

    return {
        "home": {
            "categories": [
                {"id": "skins", "count": len(cards.get("skins", {})), "path": "data/api/consumer/cards/skins/"},
                {"id": "cases", "count": len(cards.get("cases", {})), "path": "data/api/consumer/cards/cases/"},
                {"id": "knives", "count": len(filtered_refs("weapons", card_type="knife")), "path": "data/api/consumer/browse/knives.json"},
                {"id": "gloves", "count": len(filtered_refs("weapons", card_type="glove")), "path": "data/api/consumer/browse/gloves.json"},
                {"id": "capsules", "count": len(cards.get("capsules", {})), "path": "data/api/consumer/cards/capsules/"},
                {"id": "souvenir-packages", "count": len(cards.get("souvenir-packages", {})), "path": "data/api/consumer/cards/souvenir-packages/"},
                {"id": "weapons", "count": len(cards.get("weapons", {})), "path": "data/api/consumer/cards/weapons/"},
                {"id": "collections", "count": len(cards.get("collections", {})), "path": "data/api/consumer/cards/collections/"},
                {"id": "stickers", "count": len(cards.get("stickers", {})), "path": "data/api/consumer/cards/stickers/"},
                {"id": "special-pools", "count": len(cards.get("special-pools", {})), "path": "data/api/consumer/cards/special-pools/"},
                {"id": "finish-families", "count": len(overlays.get("finish-families", {})), "path": "data/api/consumer/browse/finish-families.json"},
                {"id": "rare-patterns", "count": len(overlays.get("rare-patterns", {})), "path": "data/api/consumer/browse/rare-patterns.json"},
            ]
        },
        "categories": {
            "groups": [
                {"id": group_name, "count": len(group_cards)}
                for group_name, group_cards in sorted(cards.items())
            ],
            "overlay_groups": [
                {"id": group_name, "count": len(group_cards)}
                for group_name, group_cards in sorted(overlays.items())
            ],
        },
        "collectibles": {"items": refs("collectibles")},
        "containers": {"items": refs("containers")},
        "equipment": {"items": refs("equipment")},
        "skins": {"items": refs("skins")},
        "knives": {"items": filtered_refs("weapons", card_type="knife")},
        "gloves": {"items": filtered_refs("weapons", card_type="glove")},
        "cases": {"items": refs("cases")},
        "capsules": {"items": refs("capsules")},
        "souvenir-packages": {"items": refs("souvenir-packages")},
        "weapons": {"items": refs("weapons")},
        "collections": {"items": refs("collections")},
        "stickers": {"items": refs("stickers")},
        "patches": {"items": refs("patches")},
        "graffiti": {"items": refs("graffiti")},
        "agents": {"items": refs("agents")},
        "charms": {"items": refs("charms")},
        "music-kits": {"items": refs("music-kits")},
        "tournaments": {"items": refs("tournaments")},
        "teams": {"items": refs("teams")},
        "players": {"items": refs("players")},
        "special-pools": {"items": refs("special-pools")},
        "tools": {"items": refs("tools")},
        "finish-families": {"items": overlay_refs("finish-families")},
        "rare-patterns": {"items": overlay_refs("rare-patterns")},
        "phases": {"items": overlay_refs("phases")},
        "market-constraints": {"items": overlay_refs("market-constraints")},
        "trading": {
            "overlay_groups": [
                {
                    "id": group_name,
                    "count": len(group_cards),
                    "path": f"data/api/consumer/browse/{group_name}.json",
                }
                for group_name, group_cards in sorted(overlays.items())
            ],
            "pattern_sensitive_skin_count": sum(
                1
                for card in cards.get("skins", {}).values()
                if card.get("trading", {}).get("pattern_sensitive")
            ),
            "finish_family_count": len(overlays.get("finish-families", {})),
            "phase_count": len(overlays.get("phases", {})),
        },
    }


def build_consumer_discovery(
    cards: dict[str, dict[str, dict[str, Any]]],
    overlays: dict[str, dict[str, dict[str, Any]]],
    lists: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    placeholders = {
        "agents": "<item_definition_id>",
        "capsules": "<container_id>",
        "cases": "<container_id>",
        "charms": "<keychain_definition_id>",
        "collectibles": "<item_definition_id>",
        "collections": "<collection_id>",
        "containers": "<container_id>",
        "equipment": "<item_definition_id>",
        "graffiti": "<sticker_kit_id>",
        "music-kits": "<music_definition_id>",
        "patches": "<sticker_kit_id>",
        "players": "<player_id>",
        "skin-variants": "<variant_id>",
        "skins": "<skin_id>",
        "souvenir-packages": "<container_id>",
        "special-pools": "<token>",
        "stickers": "<sticker_kit_id>",
        "teams": "<team_id>",
        "tournaments": "<event_id>",
        "tools": "<item_definition_id>",
        "weapons": "<weapon_id>",
    }
    overlay_placeholders = {
        "finish-families": "<family_id>",
        "market-constraints": "<constraint_id>",
        "phases": "<paint_kit_id>",
        "rare-patterns": "<mechanic_id>",
    }
    return {
        "entrypoints": {
            "home": "data/api/consumer/browse/home.json",
            **{
                group_name.replace("-", "_"): f"data/api/consumer/cards/{group_name}/{placeholders[group_name]}.json"
                for group_name in sorted(cards)
            },
            **{
                group_name.replace("-", "_"): f"data/api/consumer/overlays/{group_name}/{overlay_placeholders[group_name]}.json"
                for group_name in sorted(overlays)
            },
            "agent_sides": "data/api/consumer/lists/by-side/<side>.json",
            "canonical_slugs": "data/api/consumer/lists/by-canonical-slug/<canonical_slug>.json",
            "finish_family_items": "data/api/consumer/lists/by-finish-family/<family_id>.json",
            "finish_items": "data/api/consumer/lists/by-finish/<paint_kit_id>.json",
            "market_constraints_list": "data/api/consumer/lists/by-market-constraint/<constraint_id>.json",
            "market_hash_names": "data/api/consumer/lists/by-market-hash-name/<market_hash_name>.json",
            "pattern_mechanics": "data/api/consumer/lists/by-pattern-mechanic/<mechanic_id>.json",
            "qualities": "data/api/consumer/lists/by-quality/<quality>.json",
            "search_slugs": "data/api/consumer/lists/by-search-slug/<search_slug>.json",
            "skin_exteriors": "data/api/consumer/lists/by-exterior/<exterior>.json",
            "weapon_skins": "data/api/consumer/lists/by-weapon/<weapon_id>.json",
        },
        "counts": {
            group_name: len(group_cards)
            for group_name, group_cards in cards.items()
        },
        "overlay_counts": {
            group_name: len(group_cards)
            for group_name, group_cards in overlays.items()
        },
        "list_counts": {
            list_name: len(payload)
            for list_name, payload in lists.items()
        },
    }


def build_consumer_facets(
    cards: dict[str, dict[str, dict[str, Any]]],
    overlays: dict[str, dict[str, dict[str, Any]]],
    special_pools: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    collectible_groups = defaultdict(int)
    equipment_groups = defaultdict(int)
    weapon_groups = defaultdict(int)
    finish_styles = defaultdict(int)
    finish_families = defaultdict(int)
    pattern_mechanics = defaultdict(int)
    pattern_sensitivity_levels = defaultdict(int)
    support_counts = defaultdict(int)
    qualities = defaultdict(int)
    exteriors = defaultdict(int)
    pool_categories = defaultdict(int)
    for card in cards.get("collectibles", {}).values():
        collectible_groups[card["collectible_group"]] += 1
    for card in cards.get("equipment", {}).values():
        equipment_groups[card["equipment_group"]] += 1
    for card in cards.get("weapons", {}).values():
        weapon_groups[card["weapon_group"]] += 1
    for card in cards.get("skins", {}).values():
        style_name = card["finish"].get("style_name") or f"style-{card['finish'].get('style_code')}"
        finish_styles[style_name] += 1
        trading = card.get("trading", {})
        finish_family = trading.get("finish_family")
        if finish_family:
            finish_families[finish_family["id"]] += 1
        pattern_sensitivity_levels[trading.get("pattern_sensitivity", "none")] += 1
        for mechanic in trading.get("pattern_mechanics", []):
            pattern_mechanics[mechanic["id"]] += 1
        for support_name, enabled in trading.get("supports", {}).items():
            if enabled:
                support_counts[support_name] += 1
    for card in cards.get("skin-variants", {}).values():
        if card.get("quality"):
            qualities[card["quality"]] += 1
        if card.get("exterior"):
            exteriors[card["exterior"]] += 1
    for pool in special_pools.values():
        pool_categories[pool["pool_category"]] += 1
    return {
        "collectible_groups": dict(sorted(collectible_groups.items())),
        "equipment_groups": dict(sorted(equipment_groups.items())),
        "weapon_groups": dict(sorted(weapon_groups.items())),
        "finish_styles": dict(sorted(finish_styles.items())),
        "finish_families": dict(sorted(finish_families.items())),
        "pattern_mechanics": dict(sorted(pattern_mechanics.items())),
        "pattern_sensitivity": dict(sorted(pattern_sensitivity_levels.items())),
        "supports": dict(sorted(support_counts.items())),
        "qualities": dict(sorted(qualities.items())),
        "exteriors": dict(sorted(exteriors.items())),
        "market_constraints": {
            constraint_id: overlay.get("affected_item_count", 0)
            for constraint_id, overlay in sorted(overlays.get("market-constraints", {}).items())
        },
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
    rendered: dict[str, Any],
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

    fallback = generic_rendered_media_summary(
        rendered,
        "weapon",
        weapon_id,
        media_summary(assets, "weapon", weapon_id, preview_status="weapon-base-fallback"),
    )
    return {
        **fallback,
        "primary_image_png": fallback.get("primary_image_png"),
        "primary_preview_tier": None,
        "images_png": fallback.get("images_png", []),
        "preview_images": {},
        "source_texture_paths": {},
    }


def skin_variant_media_summary(
    rendered_variant: dict[str, Any] | None,
    skin_media: dict[str, Any] | None,
) -> dict[str, Any]:
    if rendered_variant is None:
        fallback_image = skin_media.get("primary_image_png") if skin_media else None
        return {
            "manifest_path": None,
            "preview_status": skin_media.get("preview_status", "unavailable") if skin_media else "unavailable",
            "image_png": fallback_image,
            "preview_tier": None,
            "source_skin_manifest_path": skin_media.get("manifest_path") if skin_media else None,
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
        "collectible": "collectibles",
        "container": "containers",
        "equipment": "equipment",
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
    resolved_token = token if token and not is_placeholder_name(token) else None
    for locale in locales:
        value = localizer.resolve(resolved_token, locale) if resolved_token else None
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


def card_ref(
    group_name: str,
    entity_id: str | int,
    name: str,
    canonical_slug: str | None,
    search_slug: str | None,
    card_type: str,
) -> dict[str, Any]:
    return {
        "id": str(entity_id),
        "name": name,
        "card_type": card_type,
        "group": group_name,
        "canonical_slug": canonical_slug,
        "search_slug": search_slug,
        "path": f"data/api/consumer/cards/{group_name}/{entity_id}.json",
    }


def first_nonempty(values: list[str] | None) -> str | None:
    if not values:
        return None
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
    return None
