from __future__ import annotations

import re
from typing import Any

from cs2_skins_api.utils import build_canonical_slug, slugify


PLACEHOLDER_NAME_RE = re.compile(r"^(?:PaintKit_[A-Za-z0-9_]+(?:_Tag)?|Item \d+)$")
PHASE_RE = re.compile(r"phase([1-4])")

STYLE_PREFIX_TOKENS = {
    "aa",
    "am",
    "anodized",
    "aq",
    "cu",
    "gs",
    "hy",
    "soch",
    "sp",
}
LEADING_ENTITY_TOKENS = {
    "ak47",
    "aug",
    "awp",
    "bayonet",
    "bloodhound",
    "bowie",
    "brokenfang",
    "butterfly",
    "canis",
    "classic",
    "cz75",
    "daggers",
    "deagle",
    "driver",
    "elite",
    "falchion",
    "famas",
    "fiveseven",
    "flip",
    "g3sg1",
    "galil",
    "glock",
    "glove",
    "gut",
    "handwrap",
    "huntsman",
    "hydra",
    "karambit",
    "knife",
    "m249",
    "m4a1s",
    "m4a4",
    "mac10",
    "mag7",
    "marbleized",
    "motorcycle",
    "mp5sd",
    "mp7",
    "mp9",
    "m9",
    "navaja",
    "negev",
    "nomad",
    "nova",
    "p2000",
    "p250",
    "p90",
    "paracord",
    "pp",
    "r8",
    "revolver",
    "sawedoff",
    "scar20",
    "sg553",
    "shadow",
    "skeleton",
    "slick",
    "specialist",
    "sport",
    "sporty",
    "ssg08",
    "stiletto",
    "survival",
    "talon",
    "tec9",
    "ump",
    "ursus",
    "usp",
    "weapon",
    "widow",
    "xm1014",
}
TOKEN_LABELS = {
    "ak47": "AK-47",
    "aug": "AUG",
    "awp": "AWP",
    "cz75": "CZ75-Auto",
    "deagle": "Desert Eagle",
    "elite": "Elite",
    "famas": "FAMAS",
    "fiveseven": "Five-SeveN",
    "g3sg1": "G3SG1",
    "m249": "M249",
    "m4a1s": "M4A1-S",
    "m4a4": "M4A4",
    "mac10": "MAC-10",
    "mag7": "MAG-7",
    "mp5sd": "MP5-SD",
    "mp7": "MP7",
    "mp9": "MP9",
    "m9": "M9",
    "p2000": "P2000",
    "p250": "P250",
    "p90": "P90",
    "pp": "PP",
    "r8": "R8",
    "scar20": "SCAR-20",
    "sg553": "SG 553",
    "ssg08": "SSG 08",
    "tec9": "Tec-9",
    "ump": "UMP-45",
    "usp": "USP-S",
    "xm1014": "XM1014",
}
CSFLOAT_CATEGORY_BY_QUALITY = {
    "normal": 1,
    "stattrak": 2,
    "souvenir": 3,
}
PATTERN_SEED_DOMAIN = {
    "field": "paint_seed",
    "minimum": 0,
    "maximum": 1000,
    "cardinality": 1001,
    "standard_opening_maximum": 999,
    "tradeup_only_seed_values": [1000],
    "deterministic": True,
}
DEFAULT_SUPPORT_FLAGS = {
    "phase_overlay": False,
    "fade_overlay": False,
    "blue_gem_overlay": False,
    "fire_and_ice_overlay": False,
    "web_overlay": False,
    "slaughter_overlay": False,
}

FINISH_FAMILY_SPECS: dict[str, dict[str, Any]] = {
    "acid-fade": {
        "name": "Acid Fade",
        "description": "Acid Fade family where deterministic seed offsets can be converted into fade-style coverage rankings.",
        "knowledge_source": "open-source-pattern-algorithm",
        "confidence": "high",
        "pattern_sensitive": True,
        "pattern_sensitivity": "high",
        "resolution_level": "paint-seed",
        "deterministic_inputs": ["paint_index", "paint_seed"],
        "float_relevance": "low",
        "primary_mechanics": ["fade-percentage"],
        "supports": {
            **DEFAULT_SUPPORT_FLAGS,
            "fade_overlay": True,
        },
    },
    "amber-fade": {
        "name": "Amber Fade",
        "description": "Amber Fade family where deterministic seed offsets can be converted into fade-style coverage rankings.",
        "knowledge_source": "open-source-pattern-algorithm",
        "confidence": "high",
        "pattern_sensitive": True,
        "pattern_sensitivity": "high",
        "resolution_level": "paint-seed",
        "deterministic_inputs": ["paint_index", "paint_seed"],
        "float_relevance": "low",
        "primary_mechanics": ["fade-percentage"],
        "supports": {
            **DEFAULT_SUPPORT_FLAGS,
            "fade_overlay": True,
        },
    },
    "blue-steel": {
        "name": "Blue Steel",
        "description": "Classic knife finish family where condition and model matter more than seed-specific overpay patterns.",
        "knowledge_source": "consumer-finish-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": False,
        "pattern_sensitivity": "none",
        "resolution_level": "finish",
        "deterministic_inputs": ["paint_index"],
        "float_relevance": "medium",
        "primary_mechanics": [],
        "supports": dict(DEFAULT_SUPPORT_FLAGS),
    },
    "boreal-forest": {
        "name": "Boreal Forest",
        "description": "Legacy camouflage knife family where consumers usually browse by finish identity and wear band rather than notable seed tiers.",
        "knowledge_source": "consumer-finish-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": False,
        "pattern_sensitivity": "none",
        "resolution_level": "finish",
        "deterministic_inputs": ["paint_index"],
        "float_relevance": "medium",
        "primary_mechanics": [],
        "supports": dict(DEFAULT_SUPPORT_FLAGS),
    },
    "bright-water": {
        "name": "Bright Water",
        "description": "Bright Water knife family where finish identity and wear dominate consumer browse flows.",
        "knowledge_source": "consumer-finish-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": False,
        "pattern_sensitivity": "none",
        "resolution_level": "finish",
        "deterministic_inputs": ["paint_index"],
        "float_relevance": "medium",
        "primary_mechanics": [],
        "supports": dict(DEFAULT_SUPPORT_FLAGS),
    },
    "case-hardened": {
        "name": "Case Hardened",
        "description": "Community trading family for seed-driven, blue-dominant patterns commonly called Blue Gems.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "high",
        "pattern_sensitive": True,
        "pattern_sensitivity": "high",
        "resolution_level": "paint-seed",
        "deterministic_inputs": ["paint_index", "paint_seed"],
        "float_relevance": "medium",
        "primary_mechanics": ["blue-gem"],
        "supports": {
            **DEFAULT_SUPPORT_FLAGS,
            "blue_gem_overlay": True,
        },
    },
    "crimson-web": {
        "name": "Crimson Web",
        "description": "Collector family where web placement and web count are seed-sensitive, while float strongly affects visible wear.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "high",
        "pattern_sensitive": True,
        "pattern_sensitivity": "high",
        "resolution_level": "paint-seed-and-float",
        "deterministic_inputs": ["paint_index", "paint_seed", "float_value"],
        "float_relevance": "high",
        "primary_mechanics": ["web-placement"],
        "supports": {
            **DEFAULT_SUPPORT_FLAGS,
            "web_overlay": True,
        },
    },
    "damascus-steel": {
        "name": "Damascus Steel",
        "description": "Layered knife finish family typically valued for finish identity, wear window, and model rather than seed-ranked patterns.",
        "knowledge_source": "consumer-finish-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": False,
        "pattern_sensitivity": "none",
        "resolution_level": "finish",
        "deterministic_inputs": ["paint_index"],
        "float_relevance": "medium",
        "primary_mechanics": [],
        "supports": dict(DEFAULT_SUPPORT_FLAGS),
    },
    "doppler": {
        "name": "Doppler",
        "description": "Phase-driven finish family with numbered phases and gem variants such as Ruby, Sapphire, and Black Pearl.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "high",
        "pattern_sensitive": True,
        "pattern_sensitivity": "medium",
        "resolution_level": "finish",
        "deterministic_inputs": ["paint_index"],
        "float_relevance": "low",
        "primary_mechanics": ["phase"],
        "supports": {
            **DEFAULT_SUPPORT_FLAGS,
            "phase_overlay": True,
        },
    },
    "emerald-web": {
        "name": "Emerald Web",
        "description": "Glove family where web placement remains pattern-sensitive and clean symmetry can matter to collectors.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": True,
        "pattern_sensitivity": "high",
        "resolution_level": "paint-seed-and-float",
        "deterministic_inputs": ["paint_index", "paint_seed", "float_value"],
        "float_relevance": "high",
        "primary_mechanics": ["web-placement"],
        "supports": {
            **DEFAULT_SUPPORT_FLAGS,
            "web_overlay": True,
        },
    },
    "fade": {
        "name": "Fade",
        "description": "Gradient finish family where collectors track fade percentage and color balance across the visible surface.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "high",
        "pattern_sensitive": True,
        "pattern_sensitivity": "high",
        "resolution_level": "paint-seed",
        "deterministic_inputs": ["paint_index", "paint_seed"],
        "float_relevance": "low",
        "primary_mechanics": ["fade-percentage"],
        "supports": {
            **DEFAULT_SUPPORT_FLAGS,
            "fade_overlay": True,
        },
    },
    "forest-ddpat": {
        "name": "Forest DDPAT",
        "description": "Forest DDPAT knife family where finish identity and exterior matter more than tracked seed tiers.",
        "knowledge_source": "consumer-finish-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": False,
        "pattern_sensitivity": "none",
        "resolution_level": "finish",
        "deterministic_inputs": ["paint_index"],
        "float_relevance": "medium",
        "primary_mechanics": [],
        "supports": dict(DEFAULT_SUPPORT_FLAGS),
    },
    "freehand": {
        "name": "Freehand",
        "description": "Freehand knife family that is typically consumed as a finish identity rather than a seed-tier market mechanic.",
        "knowledge_source": "consumer-finish-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": False,
        "pattern_sensitivity": "none",
        "resolution_level": "finish",
        "deterministic_inputs": ["paint_index"],
        "float_relevance": "medium",
        "primary_mechanics": [],
        "supports": dict(DEFAULT_SUPPORT_FLAGS),
    },
    "gamma-doppler": {
        "name": "Gamma Doppler",
        "description": "Phase-driven finish family with numbered phases and Emerald variants that matter to trading-oriented browse flows.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "high",
        "pattern_sensitive": True,
        "pattern_sensitivity": "medium",
        "resolution_level": "finish",
        "deterministic_inputs": ["paint_index"],
        "float_relevance": "low",
        "primary_mechanics": ["phase"],
        "supports": {
            **DEFAULT_SUPPORT_FLAGS,
            "phase_overlay": True,
        },
    },
    "glove-case-hardened": {
        "name": "Glove Case Hardened",
        "description": "Glove Case Hardened family where pattern distribution matters, but glove collectors do not use the same knife-oriented Blue Gem taxonomy as a universal contract.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": True,
        "pattern_sensitivity": "high",
        "resolution_level": "paint-seed",
        "deterministic_inputs": ["paint_index", "paint_seed"],
        "float_relevance": "medium",
        "primary_mechanics": [],
        "supports": dict(DEFAULT_SUPPORT_FLAGS),
    },
    "glove-fade": {
        "name": "Glove Fade",
        "description": "Pattern-sensitive glove family where color split and playside distribution matter, but knife-style fade percentages are not a stable cross-platform contract.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": True,
        "pattern_sensitivity": "high",
        "resolution_level": "paint-seed",
        "deterministic_inputs": ["paint_index", "paint_seed"],
        "float_relevance": "medium",
        "primary_mechanics": [],
        "supports": dict(DEFAULT_SUPPORT_FLAGS),
    },
    "glove-marble-fade": {
        "name": "Glove Marble Fade",
        "description": "Pattern-sensitive glove family that should not be conflated with knife Fire and Ice taxonomy.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": True,
        "pattern_sensitivity": "medium",
        "resolution_level": "paint-seed",
        "deterministic_inputs": ["paint_index", "paint_seed"],
        "float_relevance": "medium",
        "primary_mechanics": [],
        "supports": dict(DEFAULT_SUPPORT_FLAGS),
    },
    "glove-slaughter": {
        "name": "Glove Slaughter",
        "description": "Glove Slaughter family where pattern layout can matter, but the classic knife motif taxonomy is not a stable universal overlay.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": True,
        "pattern_sensitivity": "medium",
        "resolution_level": "paint-seed",
        "deterministic_inputs": ["paint_index", "paint_seed"],
        "float_relevance": "medium",
        "primary_mechanics": [],
        "supports": dict(DEFAULT_SUPPORT_FLAGS),
    },
    "heat-treated": {
        "name": "Heat Treated",
        "description": "Case-Hardened-adjacent family tracked by the community for blue-dominant, seed-driven overpay patterns.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": True,
        "pattern_sensitivity": "high",
        "resolution_level": "paint-seed",
        "deterministic_inputs": ["paint_index", "paint_seed"],
        "float_relevance": "medium",
        "primary_mechanics": ["blue-gem"],
        "supports": {
            **DEFAULT_SUPPORT_FLAGS,
            "blue_gem_overlay": True,
        },
    },
    "marble-fade": {
        "name": "Marble Fade",
        "description": "Collector family where fire-and-ice style tiers and tip color balance are seed-sensitive.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "high",
        "pattern_sensitive": True,
        "pattern_sensitivity": "high",
        "resolution_level": "paint-seed",
        "deterministic_inputs": ["paint_index", "paint_seed"],
        "float_relevance": "low",
        "primary_mechanics": ["fire-and-ice"],
        "supports": {
            **DEFAULT_SUPPORT_FLAGS,
            "fire_and_ice_overlay": True,
        },
    },
    "night": {
        "name": "Night",
        "description": "Night knife family where finish identity and clean condition matter more than tracked seed tiers.",
        "knowledge_source": "consumer-finish-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": False,
        "pattern_sensitivity": "none",
        "resolution_level": "finish",
        "deterministic_inputs": ["paint_index"],
        "float_relevance": "medium",
        "primary_mechanics": [],
        "supports": dict(DEFAULT_SUPPORT_FLAGS),
    },
    "rust-coat": {
        "name": "Rust Coat",
        "description": "Rust Coat knife family where finish identity is stable but visible appeal is strongly driven by exact float.",
        "knowledge_source": "consumer-finish-taxonomy",
        "confidence": "high",
        "pattern_sensitive": False,
        "pattern_sensitivity": "none",
        "resolution_level": "finish-and-float",
        "deterministic_inputs": ["paint_index", "float_value"],
        "float_relevance": "high",
        "primary_mechanics": [],
        "supports": dict(DEFAULT_SUPPORT_FLAGS),
    },
    "safari-mesh": {
        "name": "Safari Mesh",
        "description": "Safari Mesh knife family where finish identity and wear bands dominate consumer use cases.",
        "knowledge_source": "consumer-finish-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": False,
        "pattern_sensitivity": "none",
        "resolution_level": "finish",
        "deterministic_inputs": ["paint_index"],
        "float_relevance": "medium",
        "primary_mechanics": [],
        "supports": dict(DEFAULT_SUPPORT_FLAGS),
    },
    "scorched": {
        "name": "Scorched",
        "description": "Scorched knife family where finish identity and wear dominate consumer browse flows.",
        "knowledge_source": "consumer-finish-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": False,
        "pattern_sensitivity": "none",
        "resolution_level": "finish",
        "deterministic_inputs": ["paint_index"],
        "float_relevance": "medium",
        "primary_mechanics": [],
        "supports": dict(DEFAULT_SUPPORT_FLAGS),
    },
    "slaughter": {
        "name": "Slaughter",
        "description": "Collector family where motif placement and symmetry are tracked by pattern-sensitive traders.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": True,
        "pattern_sensitivity": "medium",
        "resolution_level": "paint-seed",
        "deterministic_inputs": ["paint_index", "paint_seed"],
        "float_relevance": "medium",
        "primary_mechanics": ["slaughter-motif"],
        "supports": {
            **DEFAULT_SUPPORT_FLAGS,
            "slaughter_overlay": True,
        },
    },
    "stained": {
        "name": "Stained",
        "description": "Stained knife family where finish identity and exact wear band are more important than seed-specific pattern tiers.",
        "knowledge_source": "consumer-finish-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": False,
        "pattern_sensitivity": "none",
        "resolution_level": "finish",
        "deterministic_inputs": ["paint_index"],
        "float_relevance": "medium",
        "primary_mechanics": [],
        "supports": dict(DEFAULT_SUPPORT_FLAGS),
    },
    "tiger-tooth": {
        "name": "Tiger Tooth",
        "description": "Tiger Tooth family where finish identity is the collector-facing contract and seed-level differentiation is not a standard overlay surface.",
        "knowledge_source": "consumer-finish-taxonomy",
        "confidence": "high",
        "pattern_sensitive": False,
        "pattern_sensitivity": "none",
        "resolution_level": "finish",
        "deterministic_inputs": ["paint_index"],
        "float_relevance": "low",
        "primary_mechanics": [],
        "supports": dict(DEFAULT_SUPPORT_FLAGS),
    },
    "ultraviolet": {
        "name": "Ultraviolet",
        "description": "Ultraviolet knife family where wear cleanliness matters more than seed-ranked pattern analytics.",
        "knowledge_source": "consumer-finish-taxonomy",
        "confidence": "high",
        "pattern_sensitive": False,
        "pattern_sensitivity": "none",
        "resolution_level": "finish-and-float",
        "deterministic_inputs": ["paint_index", "float_value"],
        "float_relevance": "high",
        "primary_mechanics": [],
        "supports": dict(DEFAULT_SUPPORT_FLAGS),
    },
    "urban-masked": {
        "name": "Urban Masked",
        "description": "Urban Masked knife family where finish identity and wear range dominate consumer-facing browse flows.",
        "knowledge_source": "consumer-finish-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": False,
        "pattern_sensitivity": "none",
        "resolution_level": "finish",
        "deterministic_inputs": ["paint_index"],
        "float_relevance": "medium",
        "primary_mechanics": [],
        "supports": dict(DEFAULT_SUPPORT_FLAGS),
    },
}

RARE_PATTERN_SPECS: dict[str, dict[str, Any]] = {
    "blue-gem": {
        "name": "Blue Gem",
        "description": "Seed-based blue-dominant patterns that trade at collector overpay tiers.",
        "knowledge_source": "community-trading-taxonomy",
        "resolution_level": "paint-seed",
        "deterministic_inputs": ["paint_index", "paint_seed"],
        "float_relevance": "medium",
        "live_item_requirements": ["paint_seed", "inspect_link"],
    },
    "fade-percentage": {
        "name": "Fade Percentage",
        "description": "Seed-based fade coverage metric used to compare premium gradient variants.",
        "knowledge_source": "community-trading-taxonomy",
        "resolution_level": "paint-seed",
        "deterministic_inputs": ["paint_index", "paint_seed"],
        "float_relevance": "low",
        "live_item_requirements": ["paint_seed", "inspect_link"],
    },
    "fire-and-ice": {
        "name": "Fire and Ice",
        "description": "Seed-sensitive Marble Fade taxonomy focused on red-blue dominance and clean tip balance.",
        "knowledge_source": "community-trading-taxonomy",
        "resolution_level": "paint-seed",
        "deterministic_inputs": ["paint_index", "paint_seed"],
        "float_relevance": "low",
        "live_item_requirements": ["paint_seed", "inspect_link"],
    },
    "phase": {
        "name": "Phase",
        "description": "Phase grouping for Doppler and Gamma Doppler finishes, including numbered phases and gem variants.",
        "knowledge_source": "derived-name-taxonomy",
        "resolution_level": "finish",
        "deterministic_inputs": ["paint_index"],
        "float_relevance": "low",
        "live_item_requirements": [],
    },
    "slaughter-motif": {
        "name": "Slaughter Motif",
        "description": "Pattern-sensitive motif grouping used by collectors to compare desirable Slaughter layouts.",
        "knowledge_source": "community-trading-taxonomy",
        "resolution_level": "paint-seed",
        "deterministic_inputs": ["paint_index", "paint_seed"],
        "float_relevance": "medium",
        "live_item_requirements": ["paint_seed", "inspect_link"],
    },
    "web-placement": {
        "name": "Web Placement",
        "description": "Pattern-sensitive web count and placement mechanic tracked on web-based finishes.",
        "knowledge_source": "community-trading-taxonomy",
        "resolution_level": "paint-seed-and-float",
        "deterministic_inputs": ["paint_index", "paint_seed", "float_value"],
        "float_relevance": "high",
        "live_item_requirements": ["paint_seed", "inspect_link"],
    },
}

MARKET_CONSTRAINT_SPECS: dict[str, dict[str, Any]] = {
    "cannot-trade": {
        "name": "Cannot Trade",
        "description": "Source item definition explicitly sets the `cannot trade` attribute.",
        "knowledge_source": "source-backed-attribute",
        "source_attributes": ["cannot trade"],
    },
    "requires-float-value": {
        "name": "Exact Float Value Required",
        "description": "Precise instance evaluation for this mechanic needs the concrete float value from a live item payload.",
        "knowledge_source": "derived-instance-requirement",
        "required_instance_fields": ["float_value"],
    },
    "requires-inspect-link": {
        "name": "Inspect Link Required",
        "description": "This mechanic commonly requires a concrete inspect link or equivalent live item payload to resolve instance-level state.",
        "knowledge_source": "derived-instance-requirement",
        "required_instance_fields": ["d_param"],
    },
    "requires-paint-seed": {
        "name": "Paint Seed Required",
        "description": "Precise pattern classification for this mechanic needs the live paint seed value.",
        "knowledge_source": "derived-instance-requirement",
        "required_instance_fields": ["paint_seed"],
    },
    "live-item-market-state": {
        "name": "Live Item Market State Required",
        "description": "Exact float, paint seed, stickers, inspect link, and trade timers require a concrete live item or listing payload.",
        "knowledge_source": "external-listing-contract",
        "required_instance_fields": ["asset_id", "d_param", "float_value", "paint_seed", "stickers", "tradable"],
    },
}


def is_placeholder_name(value: str | None) -> bool:
    if value is None:
        return False
    return bool(PLACEHOLDER_NAME_RE.match(str(value).strip()))


def humanize_finish_codename(codename: str | None) -> str | None:
    if not codename:
        return None
    normalized = str(codename).strip().lower().replace("-", "_")
    tokens = [token for token in normalized.split("_") if token]
    if not tokens:
        return None
    while tokens and tokens[0] in STYLE_PREFIX_TOKENS:
        tokens = tokens[1:]
    while len(tokens) > 1 and tokens[0] in LEADING_ENTITY_TOKENS:
        tokens = tokens[1:]
    if len(tokens) > 1 and tokens[-1].isdigit():
        tokens = tokens[:-1]
    if not tokens:
        tokens = [token for token in normalized.split("_") if token]
    return " ".join(humanize_token(token) for token in tokens) or None


def humanize_token(token: str) -> str:
    lowered = token.lower()
    if lowered in TOKEN_LABELS:
        return TOKEN_LABELS[lowered]
    if len(lowered) <= 2 and lowered.isalpha():
        return lowered.upper()
    return lowered.replace("'", "").capitalize()


def normalized_finish_name(display_name: str | None, codename: str | None) -> tuple[str | None, str]:
    if display_name and not is_placeholder_name(display_name):
        return display_name, "localized"
    fallback = humanize_finish_codename(codename)
    if fallback:
        return fallback, "codename-fallback"
    if display_name:
        return display_name, "placeholder"
    if codename:
        return codename, "placeholder"
    return None, "missing"


def finish_family_id(finish: dict[str, Any], weapon_group: str | None = None) -> str | None:
    name = str(finish.get("name") or "").strip().lower()
    group = str(weapon_group or "").strip().lower()
    if name == "acid fade":
        return "acid-fade"
    if name == "amber fade":
        return "amber-fade"
    if group == "glove":
        if name == "fade":
            return "glove-fade"
        if name == "marble fade":
            return "glove-marble-fade"
        if name == "case hardened":
            return "glove-case-hardened"
        if name == "slaughter":
            return "glove-slaughter"
    if name == "gamma doppler":
        return "gamma-doppler"
    if name == "doppler":
        return "doppler"
    if name == "marble fade":
        return "marble-fade"
    if name == "fade":
        return "fade"
    if name == "blue steel":
        return "blue-steel"
    if name == "boreal forest":
        return "boreal-forest"
    if name == "bright water":
        return "bright-water"
    if name == "case hardened":
        return "case-hardened"
    if name == "damascus steel":
        return "damascus-steel"
    if name == "forest ddpat":
        return "forest-ddpat"
    if name == "freehand":
        return "freehand"
    if name == "heat treated":
        return "heat-treated"
    if name == "night":
        return "night"
    if name == "rust coat":
        return "rust-coat"
    if name == "safari mesh":
        return "safari-mesh"
    if name == "scorched":
        return "scorched"
    if "crimson web" in name:
        return "crimson-web"
    if "emerald web" in name:
        return "emerald-web"
    if name == "slaughter":
        return "slaughter"
    if name == "stained":
        return "stained"
    if name == "tiger tooth":
        return "tiger-tooth"
    if name == "ultraviolet":
        return "ultraviolet"
    if name == "urban masked":
        return "urban-masked"
    return None


def finish_family_spec(family_id: str | None) -> dict[str, Any] | None:
    if family_id is None:
        return None
    return FINISH_FAMILY_SPECS.get(family_id)


def rare_pattern_mechanics(family_id: str | None) -> list[str]:
    spec = finish_family_spec(family_id)
    if spec is None:
        return []
    return list(spec.get("primary_mechanics", []))


def pattern_sensitivity(family_id: str | None) -> str:
    spec = finish_family_spec(family_id)
    if spec is None:
        return "none"
    return spec.get("pattern_sensitivity", "none")


def support_flags(family_id: str | None) -> dict[str, bool]:
    spec = finish_family_spec(family_id)
    if spec is None:
        return dict(DEFAULT_SUPPORT_FLAGS)
    return dict(spec.get("supports", {}))


def family_resolution_level(family_id: str | None) -> str:
    spec = finish_family_spec(family_id)
    if spec is None:
        return "finish"
    return spec.get("resolution_level", "finish")


def family_deterministic_inputs(family_id: str | None) -> list[str]:
    spec = finish_family_spec(family_id)
    if spec is None:
        return ["paint_index"]
    return list(spec.get("deterministic_inputs", ["paint_index"]))


def family_seed_domain(family_id: str | None) -> dict[str, Any] | None:
    if family_resolution_level(family_id) not in {"paint-seed", "paint-seed-and-float"}:
        return None
    return dict(PATTERN_SEED_DOMAIN)


def family_float_relevance(family_id: str | None) -> str:
    spec = finish_family_spec(family_id)
    if spec is None:
        return "medium"
    return spec.get("float_relevance", "medium")


def supports_paint_seed_filter(family_id: str | None) -> bool:
    return family_resolution_level(family_id) in {"paint-seed", "paint-seed-and-float"}


def rare_pattern_spec(mechanic_id: str | None) -> dict[str, Any] | None:
    if mechanic_id is None:
        return None
    return RARE_PATTERN_SPECS.get(mechanic_id)


def rare_pattern_resolution_level(mechanic_id: str | None) -> str:
    spec = rare_pattern_spec(mechanic_id)
    if spec is None:
        return "finish"
    return spec.get("resolution_level", "finish")


def rare_pattern_deterministic_inputs(mechanic_id: str | None) -> list[str]:
    spec = rare_pattern_spec(mechanic_id)
    if spec is None:
        return ["paint_index"]
    return list(spec.get("deterministic_inputs", ["paint_index"]))


def rare_pattern_seed_domain(mechanic_id: str | None) -> dict[str, Any] | None:
    if rare_pattern_resolution_level(mechanic_id) not in {"paint-seed", "paint-seed-and-float"}:
        return None
    return dict(PATTERN_SEED_DOMAIN)


def rare_pattern_float_relevance(mechanic_id: str | None) -> str:
    spec = rare_pattern_spec(mechanic_id)
    if spec is None:
        return "medium"
    return spec.get("float_relevance", "medium")


def phase_metadata(finish: dict[str, Any], family_id: str | None) -> dict[str, Any] | None:
    if family_id not in {"doppler", "gamma-doppler"}:
        return None
    codename = str(finish.get("codename") or "").lower()
    phase_code = None
    phase_name = None
    phase_kind = None
    if "emerald" in codename:
        phase_code = "emerald"
        phase_name = "Emerald"
        phase_kind = "gem"
    elif "ruby" in codename:
        phase_code = "ruby"
        phase_name = "Ruby"
        phase_kind = "gem"
    elif "sapphire" in codename:
        phase_code = "sapphire"
        phase_name = "Sapphire"
        phase_kind = "gem"
    elif "blackpearl" in codename:
        phase_code = "black-pearl"
        phase_name = "Black Pearl"
        phase_kind = "gem"
    else:
        match = PHASE_RE.search(codename)
        if match:
            phase_code = f"phase-{match.group(1)}"
            phase_name = f"Phase {match.group(1)}"
            phase_kind = "numbered"
    if phase_code is None:
        return None
    family_name = finish_family_spec(family_id)["name"]
    return {
        "id": str(finish["id"]),
        "finish_id": str(finish["id"]),
        "phase_code": phase_code,
        "phase_name": phase_name,
        "phase_kind": phase_kind,
        "phase_group": family_id,
        "name": f"{family_name} {phase_name}",
        "canonical_slug": build_canonical_slug(f"{finish.get('canonical_slug')}-{phase_code}", finish["id"]),
        "search_slug": slugify(f"{family_name} {phase_name}"),
    }


def csfloat_category(quality: str | None) -> int | None:
    if quality is None:
        return None
    return CSFLOAT_CATEGORY_BY_QUALITY.get(str(quality))


def variant_float_window(
    skin_wear: dict[str, Any],
    exterior: dict[str, Any] | None,
) -> dict[str, float] | None:
    if exterior is None:
        return None
    skin_min = skin_wear.get("min_float")
    skin_max = skin_wear.get("max_float")
    exterior_min = exterior.get("min_float")
    exterior_max = exterior.get("max_float")
    if None in {skin_min, skin_max, exterior_min, exterior_max}:
        return None
    min_float = max(float(skin_min), float(exterior_min))
    max_float = min(float(skin_max), float(exterior_max))
    if max_float < min_float:
        return None
    return {
        "min_float": round(min_float, 6),
        "max_float": round(max_float, 6),
    }


def source_market_flags(record: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(record, dict):
        return {
            "trade_state": "not-explicit",
            "cannot_trade": False,
        }
    resolved = record.get("resolved", {})
    attributes = resolved.get("attributes") if isinstance(resolved.get("attributes"), dict) else {}
    cannot_trade = str(attributes.get("cannot trade")) == "1"
    return {
        "trade_state": "cannot-trade" if cannot_trade else "not-explicit",
        "cannot_trade": cannot_trade,
    }
