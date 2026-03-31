from __future__ import annotations

from typing import Any


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

BONUS_RULE_SPECIAL_POOLS = {
    "all_entries_as_additional_drops",
    "match_highlight_reel_keychain",
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


def special_pool_category(token: str) -> str:
    if token in GLOVE_POOL_RULES:
        return "glove"
    if (
        token in LEGACY_KNIFE_POOL_WEAPONS
        or token in CHROMA_KNIFE_POOL_WEAPONS
        or token in GAMMA_KNIFE_POOL_WEAPONS
    ):
        return "knife"
    if token in BONUS_RULE_SPECIAL_POOLS:
        return "bonus-rule"
    return "special-item"


def special_pool_expansion_status(token: str, paint_kits: dict[str, dict[str, Any]], weapons: dict[str, dict[str, Any]]) -> str:
    if token in BONUS_RULE_SPECIAL_POOLS:
        return "rule"
    if build_special_pool_candidate_specs(token, paint_kits, weapons):
        return "exact-candidates"
    return "token-only"


def build_special_pool_candidate_specs(
    token: str,
    paint_kits: dict[str, dict[str, Any]],
    weapons: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if token in GLOVE_POOL_RULES:
        pool_rule = GLOVE_POOL_RULES[token]
        candidates = []
        for paint in paint_kits.values():
            if classify_glove_pool(paint) != pool_rule:
                continue
            family = classify_glove_family(paint)
            weapon_id = GLOVE_WEAPON_BY_FAMILY.get(family)
            if weapon_id is None or str(weapon_id) not in weapons:
                continue
            candidates.append(
                {
                    "weapon_id": weapon_id,
                    "paint_kit_id": int(paint["id"]),
                    "category": "glove",
                    "expansion_rule": pool_rule,
                }
            )
        return sorted(candidates, key=lambda row: (row["weapon_id"], row["paint_kit_id"]))

    if token in LEGACY_KNIFE_POOL_WEAPONS:
        return build_knife_pool_candidate_specs(
            weapon_ids=LEGACY_KNIFE_POOL_WEAPONS[token],
            paint_kit_ids=LEGACY_KNIFE_PAINT_IDS,
            weapons=weapons,
            expansion_rule="legacy-knives",
        )
    if token in CHROMA_KNIFE_POOL_WEAPONS:
        return build_knife_pool_candidate_specs(
            weapon_ids=CHROMA_KNIFE_POOL_WEAPONS[token],
            paint_kit_ids=CHROMA_KNIFE_FAMILY_PAINT_IDS,
            weapons=weapons,
            expansion_rule="chroma-knives",
        )
    if token in GAMMA_KNIFE_POOL_WEAPONS:
        return build_knife_pool_candidate_specs(
            weapon_ids=GAMMA_KNIFE_POOL_WEAPONS[token],
            paint_kit_ids=GAMMA_KNIFE_FAMILY_PAINT_IDS,
            weapons=weapons,
            expansion_rule="gamma-knives",
        )
    return []


def build_knife_pool_candidate_specs(
    weapon_ids: list[int],
    paint_kit_ids: list[int],
    weapons: dict[str, dict[str, Any]],
    expansion_rule: str,
) -> list[dict[str, Any]]:
    candidates = []
    for weapon_id in weapon_ids:
        if str(weapon_id) not in weapons:
            continue
        for paint_kit_id in paint_kit_ids:
            candidates.append(
                {
                    "weapon_id": weapon_id,
                    "paint_kit_id": paint_kit_id,
                    "category": "knife",
                    "expansion_rule": expansion_rule,
                }
            )
    return sorted(candidates, key=lambda row: (row["weapon_id"], row["paint_kit_id"]))
