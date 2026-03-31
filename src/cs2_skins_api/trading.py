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

FINISH_FAMILY_SPECS: dict[str, dict[str, Any]] = {
    "case-hardened": {
        "name": "Case Hardened",
        "description": "Community trading family for seed-driven, blue-dominant patterns commonly called Blue Gems.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "high",
        "pattern_sensitive": True,
        "pattern_sensitivity": "high",
        "primary_mechanics": ["blue-gem"],
        "supports": {
            "phase_overlay": False,
            "fade_overlay": False,
            "blue_gem_overlay": True,
            "fire_and_ice_overlay": False,
            "web_overlay": False,
            "slaughter_overlay": False,
        },
    },
    "crimson-web": {
        "name": "Crimson Web",
        "description": "Collector family where web placement and web count are seed-sensitive, while float strongly affects visible wear.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "high",
        "pattern_sensitive": True,
        "pattern_sensitivity": "high",
        "primary_mechanics": ["web-placement"],
        "supports": {
            "phase_overlay": False,
            "fade_overlay": False,
            "blue_gem_overlay": False,
            "fire_and_ice_overlay": False,
            "web_overlay": True,
            "slaughter_overlay": False,
        },
    },
    "doppler": {
        "name": "Doppler",
        "description": "Phase-driven finish family with numbered phases and gem variants such as Ruby, Sapphire, and Black Pearl.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "high",
        "pattern_sensitive": True,
        "pattern_sensitivity": "medium",
        "primary_mechanics": ["phase"],
        "supports": {
            "phase_overlay": True,
            "fade_overlay": False,
            "blue_gem_overlay": False,
            "fire_and_ice_overlay": False,
            "web_overlay": False,
            "slaughter_overlay": False,
        },
    },
    "emerald-web": {
        "name": "Emerald Web",
        "description": "Glove family where web placement remains pattern-sensitive and clean symmetry can matter to collectors.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": True,
        "pattern_sensitivity": "high",
        "primary_mechanics": ["web-placement"],
        "supports": {
            "phase_overlay": False,
            "fade_overlay": False,
            "blue_gem_overlay": False,
            "fire_and_ice_overlay": False,
            "web_overlay": True,
            "slaughter_overlay": False,
        },
    },
    "fade": {
        "name": "Fade",
        "description": "Gradient finish family where collectors track fade percentage and color balance across the visible surface.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "high",
        "pattern_sensitive": True,
        "pattern_sensitivity": "high",
        "primary_mechanics": ["fade-percentage"],
        "supports": {
            "phase_overlay": False,
            "fade_overlay": True,
            "blue_gem_overlay": False,
            "fire_and_ice_overlay": False,
            "web_overlay": False,
            "slaughter_overlay": False,
        },
    },
    "gamma-doppler": {
        "name": "Gamma Doppler",
        "description": "Phase-driven finish family with numbered phases and Emerald variants that matter to trading-oriented browse flows.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "high",
        "pattern_sensitive": True,
        "pattern_sensitivity": "medium",
        "primary_mechanics": ["phase"],
        "supports": {
            "phase_overlay": True,
            "fade_overlay": False,
            "blue_gem_overlay": False,
            "fire_and_ice_overlay": False,
            "web_overlay": False,
            "slaughter_overlay": False,
        },
    },
    "heat-treated": {
        "name": "Heat Treated",
        "description": "Case-Hardened-adjacent family tracked by the community for blue-dominant, seed-driven overpay patterns.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": True,
        "pattern_sensitivity": "high",
        "primary_mechanics": ["blue-gem"],
        "supports": {
            "phase_overlay": False,
            "fade_overlay": False,
            "blue_gem_overlay": True,
            "fire_and_ice_overlay": False,
            "web_overlay": False,
            "slaughter_overlay": False,
        },
    },
    "marble-fade": {
        "name": "Marble Fade",
        "description": "Collector family where fire-and-ice style tiers and tip color balance are seed-sensitive.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "high",
        "pattern_sensitive": True,
        "pattern_sensitivity": "high",
        "primary_mechanics": ["fire-and-ice"],
        "supports": {
            "phase_overlay": False,
            "fade_overlay": False,
            "blue_gem_overlay": False,
            "fire_and_ice_overlay": True,
            "web_overlay": False,
            "slaughter_overlay": False,
        },
    },
    "slaughter": {
        "name": "Slaughter",
        "description": "Collector family where motif placement and symmetry are tracked by pattern-sensitive traders.",
        "knowledge_source": "community-trading-taxonomy",
        "confidence": "medium",
        "pattern_sensitive": True,
        "pattern_sensitivity": "medium",
        "primary_mechanics": ["slaughter-motif"],
        "supports": {
            "phase_overlay": False,
            "fade_overlay": False,
            "blue_gem_overlay": False,
            "fire_and_ice_overlay": False,
            "web_overlay": False,
            "slaughter_overlay": True,
        },
    },
}

RARE_PATTERN_SPECS: dict[str, dict[str, Any]] = {
    "blue-gem": {
        "name": "Blue Gem",
        "description": "Seed-based blue-dominant patterns that trade at collector overpay tiers.",
        "knowledge_source": "community-trading-taxonomy",
        "live_item_requirements": ["paint_seed", "inspect_link"],
    },
    "fade-percentage": {
        "name": "Fade Percentage",
        "description": "Seed-based fade coverage metric used to compare premium gradient variants.",
        "knowledge_source": "community-trading-taxonomy",
        "live_item_requirements": ["paint_seed", "inspect_link"],
    },
    "fire-and-ice": {
        "name": "Fire and Ice",
        "description": "Seed-sensitive Marble Fade taxonomy focused on red-blue dominance and clean tip balance.",
        "knowledge_source": "community-trading-taxonomy",
        "live_item_requirements": ["paint_seed", "inspect_link"],
    },
    "phase": {
        "name": "Phase",
        "description": "Phase grouping for Doppler and Gamma Doppler finishes, including numbered phases and gem variants.",
        "knowledge_source": "derived-name-taxonomy",
        "live_item_requirements": [],
    },
    "slaughter-motif": {
        "name": "Slaughter Motif",
        "description": "Pattern-sensitive motif grouping used by collectors to compare desirable Slaughter layouts.",
        "knowledge_source": "community-trading-taxonomy",
        "live_item_requirements": ["paint_seed", "inspect_link"],
    },
    "web-placement": {
        "name": "Web Placement",
        "description": "Pattern-sensitive web count and placement mechanic tracked on web-based finishes.",
        "knowledge_source": "community-trading-taxonomy",
        "live_item_requirements": ["paint_seed", "inspect_link"],
    },
}

MARKET_CONSTRAINT_SPECS: dict[str, dict[str, Any]] = {
    "cannot-trade": {
        "name": "Cannot Trade",
        "description": "Source item definition explicitly sets the `cannot trade` attribute.",
        "knowledge_source": "source-backed-attribute",
    },
    "live-item-market-state": {
        "name": "Live Item Market State Required",
        "description": "Exact float, paint seed, stickers, inspect link, and trade timers require a concrete live item or listing payload.",
        "knowledge_source": "external-listing-contract",
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


def finish_family_id(finish: dict[str, Any]) -> str | None:
    name = str(finish.get("name") or "").strip().lower()
    if name == "gamma doppler":
        return "gamma-doppler"
    if name == "doppler":
        return "doppler"
    if name == "marble fade":
        return "marble-fade"
    if name == "fade":
        return "fade"
    if name == "case hardened":
        return "case-hardened"
    if name == "heat treated":
        return "heat-treated"
    if "crimson web" in name:
        return "crimson-web"
    if "emerald web" in name:
        return "emerald-web"
    if name == "slaughter":
        return "slaughter"
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
        return {
            "phase_overlay": False,
            "fade_overlay": False,
            "blue_gem_overlay": False,
            "fire_and_ice_overlay": False,
            "web_overlay": False,
            "slaughter_overlay": False,
        }
    return dict(spec.get("supports", {}))


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
