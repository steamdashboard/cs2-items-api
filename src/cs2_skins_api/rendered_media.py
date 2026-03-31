from __future__ import annotations

import os
import platform
import shutil
import stat
import subprocess
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

import vpk

from cs2_skins_api.utils import ensure_dir, reset_dir, unique_list


VRF_VERSION = "18.0"
VRF_RELEASE_BASE = f"https://github.com/ValveResourceFormat/ValveResourceFormat/releases/download/{VRF_VERSION}"
VRF_ASSETS = {
    ("linux", "x86_64"): "cli-linux-x64.zip",
    ("linux", "amd64"): "cli-linux-x64.zip",
    ("linux", "aarch64"): "cli-linux-arm64.zip",
    ("linux", "arm64"): "cli-linux-arm64.zip",
    ("linux", "armv7l"): "cli-linux-arm.zip",
    ("linux", "armv8l"): "cli-linux-arm.zip",
    ("darwin", "x86_64"): "cli-macos-x64.zip",
    ("darwin", "arm64"): "cli-macos-arm64.zip",
    ("windows", "amd64"): "cli-windows-x64.zip",
    ("windows", "x86_64"): "cli-windows-x64.zip",
    ("windows", "arm64"): "cli-windows-arm64.zip",
}
PREVIEW_TIERS = ("light", "medium", "heavy")
EXTERIOR_TO_TIER = {
    "factory-new": "light",
    "minimal-wear": "light",
    "field-tested": "medium",
    "well-worn": "heavy",
    "battle-scarred": "heavy",
    "vanilla": "light",
}
RENDERED_GENERIC_ENTITY_FOLDERS = {
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


def build_rendered_media(
    pak_path: Path,
    api_assets: dict[str, dict[str, Any]],
    skins: dict[str, dict[str, Any]],
    skin_variants: dict[str, dict[str, Any]],
    root: Path,
    mode: str = "png",
) -> dict[str, Any]:
    if mode == "none":
        return empty_rendered_dataset(mode)
    if mode != "png":
        raise ValueError(f"Unsupported render mode: {mode}")

    archive = vpk.open(str(pak_path))
    archive_paths = set(archive)

    staging_root = root / ".cache/rendered-media"
    input_root = staging_root / "input"
    output_root = staging_root / "output"
    reset_dir(staging_root)
    ensure_dir(input_root)
    ensure_dir(output_root)

    stats = Counter()
    stats["mode"] = mode
    unresolved: list[dict[str, Any]] = []
    skin_preview_specs: dict[str, dict[str, Any]] = {}
    generic_preview_specs: dict[str, dict[str, Any]] = {}
    generic_target_counts: Counter[str] = Counter()
    generic_target_total = 0

    for skin_id, skin in skins.items():
        preview_sources = resolve_skin_preview_sources(skin, archive_paths)
        if not preview_sources:
            if skin["weapon"]["weapon_group"] in {"knife", "glove"}:
                stats["skins_with_weapon_fallback_only"] += 1
                continue
            unresolved.append(
                {
                    "entity_type": "skin",
                    "id": skin_id,
                    "name": skin["name"],
                    "reason": "preview-textures-not-found",
                    "weapon_codename": skin["weapon"]["codename"],
                    "finish_codename": skin["finish"]["codename"],
                }
            )
            continue

        input_dir = input_root / "skins" / skin_id
        ensure_dir(input_dir)
        for tier, source_path in preview_sources.items():
            staged_source = input_dir / f"{tier}.vtex_c"
            staged_source.write_bytes(archive.get_file(source_path).read())
            stats["staged_source_files"] += 1

        skin_preview_specs[skin_id] = {
            "id": skin_id,
            "name": skin["name"],
            "source_texture_paths": preview_sources,
            "semantic_paths": {
                tier: f"data/api/media/rendered/files/skins/{skin_id}/{tier}.png"
                for tier in preview_sources
            },
        }

    for asset_id, asset in api_assets.items():
        entity_type = asset["entity_type"]
        folder_name = RENDERED_GENERIC_ENTITY_FOLDERS.get(entity_type)
        if folder_name is None:
            continue
        generic_target_total += 1
        generic_target_counts[folder_name] += 1

        source_texture_path = resolve_primary_entity_texture(asset)
        entity_id = str(asset["entity_id"])
        if source_texture_path is None:
            unresolved.append(
                {
                    "entity_type": entity_type,
                    "id": entity_id,
                    "name": asset["name"],
                    "reason": "primary-texture-not-found",
                    "asset_id": asset_id,
                }
            )
            continue

        input_dir = input_root / folder_name / entity_id
        ensure_dir(input_dir)
        staged_source = input_dir / "primary.vtex_c"
        staged_source.write_bytes(archive.get_file(source_texture_path).read())
        stats["staged_source_files"] += 1
        generic_preview_specs[asset_id] = {
            "asset_id": asset_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "folder_name": folder_name,
            "name": asset["name"],
            "source_texture_path": source_texture_path,
            "semantic_path": f"data/api/media/rendered/files/{folder_name}/{entity_id}/primary.png",
            "manifest_path": f"data/api/media/rendered/manifests/{folder_name}/{entity_id}.json",
        }

    if skin_preview_specs or generic_preview_specs:
        vrf_cli = ensure_vrf_cli(root)
        run_vrf_texture_export(vrf_cli, input_root, output_root)

    skin_manifests: dict[str, dict[str, Any]] = {}
    for skin_id, spec in skin_preview_specs.items():
        preview_images = {}
        available_tiers = []
        for tier in PREVIEW_TIERS:
            semantic_path = spec["semantic_paths"].get(tier)
            if not semantic_path:
                continue
            rendered_file = output_root / "skins" / skin_id / f"{tier}.png"
            if not rendered_file.exists():
                unresolved.append(
                    {
                        "entity_type": "skin",
                        "id": skin_id,
                        "name": spec["name"],
                        "reason": "render-output-missing",
                        "preview_tier": tier,
                        "source_texture_path": spec["source_texture_paths"].get(tier),
                    }
                )
                continue
            preview_images[tier] = semantic_path
            available_tiers.append(tier)
            stats["rendered_png_files"] += 1

        if not preview_images:
            continue

        primary_tier = choose_available_tier(preview_images, "light")
        skin_manifests[skin_id] = {
            "id": skin_id,
            "entity_type": "skin",
            "entity_id": skin_id,
            "name": spec["name"],
            "preview_status": "rendered",
            "preview_images": preview_images,
            "available_preview_tiers": available_tiers,
            "primary_preview_tier": primary_tier,
            "primary_preview_path": preview_images[primary_tier],
            "source_texture_paths": spec["source_texture_paths"],
            "manifest_path": f"data/api/media/rendered/manifests/skins/{skin_id}.json",
        }

    variant_manifests: dict[str, dict[str, Any]] = {}
    for variant_id, variant in skin_variants.items():
        skin_manifest = skin_manifests.get(variant["skin_id"])
        if skin_manifest is None:
            skin = skins.get(variant["skin_id"])
            if skin and skin["weapon"]["weapon_group"] in {"knife", "glove"}:
                stats["skin_variants_with_weapon_fallback_only"] += 1
                continue
            unresolved.append(
                {
                    "entity_type": "skin-variant",
                    "id": variant_id,
                    "name": variant["market_hash_name"],
                    "reason": "skin-preview-missing",
                    "skin_id": variant["skin_id"],
                }
            )
            continue

        requested_tier = EXTERIOR_TO_TIER.get(variant["exterior"], "medium")
        preview_tier = choose_available_tier(skin_manifest["preview_images"], requested_tier)
        variant_manifests[variant_id] = {
            "id": variant_id,
            "entity_type": "skin-variant",
            "entity_id": variant_id,
            "skin_id": variant["skin_id"],
            "name": variant["market_hash_name"],
            "quality": variant["quality"],
            "exterior": variant["exterior"],
            "exterior_name": variant["exterior_name"],
            "preview_status": "shared-skin-render",
            "preview_tier": preview_tier,
            "image_path": skin_manifest["preview_images"][preview_tier],
            "source_skin_manifest_path": skin_manifest["manifest_path"],
            "manifest_path": f"data/api/media/rendered/manifests/skin-variants/{variant_id}.json",
        }

    generic_manifests: dict[str, dict[str, dict[str, Any]]] = {
        folder_name: {}
        for folder_name in sorted(set(RENDERED_GENERIC_ENTITY_FOLDERS.values()))
    }
    for spec in generic_preview_specs.values():
        rendered_file = output_root / spec["folder_name"] / spec["entity_id"] / "primary.png"
        if not rendered_file.exists():
            unresolved.append(
                {
                    "entity_type": spec["entity_type"],
                    "id": spec["entity_id"],
                    "name": spec["name"],
                    "reason": "render-output-missing",
                    "asset_id": spec["asset_id"],
                    "source_texture_path": spec["source_texture_path"],
                }
            )
            continue
        generic_manifests[spec["folder_name"]][spec["entity_id"]] = {
            "id": spec["entity_id"],
            "entity_type": spec["entity_type"],
            "entity_id": spec["entity_id"],
            "name": spec["name"],
            "preview_status": "rendered",
            "image_path": spec["semantic_path"],
            "source_texture_path": spec["source_texture_path"],
            "manifest_path": spec["manifest_path"],
        }
        stats["rendered_png_files"] += 1

    stats["skins"] = len(skins)
    stats["skins_with_rendered_previews"] = len(skin_manifests)
    stats["skins_without_rendered_previews"] = len(skins) - len(skin_manifests)
    stats["skin_variants"] = len(skin_variants)
    stats["skin_variants_with_rendered_preview"] = len(variant_manifests)
    stats["skin_variants_without_rendered_preview"] = len(skin_variants) - len(variant_manifests)
    stats["generic_entities"] = generic_target_total
    stats["generic_entities_with_rendered_preview"] = sum(len(group) for group in generic_manifests.values())
    stats["generic_entities_without_rendered_preview"] = generic_target_total - stats["generic_entities_with_rendered_preview"]
    for folder_name, manifests in generic_manifests.items():
        stats[f"{folder_name}"] = len(manifests)
        stats[f"{folder_name}_targets"] = generic_target_counts[folder_name]
        stats[f"{folder_name}_without_rendered_preview"] = generic_target_counts[folder_name] - len(manifests)
    stats["unresolved_total"] = len(unresolved)

    staged_files = {}
    if output_root.exists():
        for png in output_root.rglob("*.png"):
            relative = png.relative_to(output_root)
            staged_files[f"data/api/media/rendered/files/{relative.as_posix()}"] = str(png)

    return {
        "mode": mode,
        "staging_root": str(output_root),
        "staged_files": staged_files,
        "entities": generic_manifests,
        "skins": skin_manifests,
        "skin_variants": variant_manifests,
        "stats": dict(stats),
        "unresolved": sorted(unresolved, key=lambda row: (row["entity_type"], row["id"])),
    }


def empty_rendered_dataset(mode: str) -> dict[str, Any]:
    return {
        "mode": mode,
        "staging_root": None,
        "staged_files": {},
        "entities": {
            folder_name: {}
            for folder_name in sorted(set(RENDERED_GENERIC_ENTITY_FOLDERS.values()))
        },
        "skins": {},
        "skin_variants": {},
        "stats": {
            "mode": mode,
            "generic_entities": 0,
            "generic_entities_with_rendered_preview": 0,
            "generic_entities_without_rendered_preview": 0,
            "skins_with_weapon_fallback_only": 0,
            "skins": 0,
            "skins_with_rendered_previews": 0,
            "skins_without_rendered_previews": 0,
            "skin_variants_with_weapon_fallback_only": 0,
            "skin_variants": 0,
            "skin_variants_with_rendered_preview": 0,
            "skin_variants_without_rendered_preview": 0,
            "rendered_png_files": 0,
            "staged_source_files": 0,
            "unresolved_total": 0,
        },
        "unresolved": [],
    }


def resolve_skin_preview_sources(skin: dict[str, Any], archive_paths: set[str]) -> dict[str, str]:
    weapon_codename = str(skin["weapon"]["codename"])
    finish_codename = str(skin["finish"]["codename"])
    candidates = [finish_codename]
    lowered = finish_codename.lower()
    if lowered != finish_codename:
        candidates.append(lowered)

    for finish_candidate in unique_list(candidates):
        preview_sources = {}
        for tier in PREVIEW_TIERS:
            source_path = (
                f"panorama/images/econ/default_generated/"
                f"{weapon_codename}_{finish_candidate}_{tier}_png.vtex_c"
            )
            if source_path in archive_paths:
                preview_sources[tier] = source_path
        if preview_sources:
            return preview_sources

    return {}


def resolve_primary_entity_texture(asset: dict[str, Any]) -> str | None:
    entity_type = asset["entity_type"]
    resolved_refs = asset.get("resolved_refs", {})

    if entity_type in {"weapon", "equipment", "collectible", "container", "charm", "music-kit", "tool"}:
        path = choose_preferred_texture(
            resolved_refs.get("image_inventory", []),
            exclude_tokens=("_store_png.vtex_c", "_square_png.vtex_c"),
        )
        if path is not None:
            return path
        weapon_name = str(asset.get("name", "")).lower()
        weapon_codename = str(asset.get("codename", "")).lower()
        if entity_type == "weapon" and (
            "gloves" in weapon_name
            or "wraps" in weapon_name
            or "glove" in weapon_codename
            or "handwrap" in weapon_codename
        ):
            return "panorama/images/econ/weapons/base_weapons/t_gloves_png.vtex_c"
        return None

    if entity_type == "agent":
        return choose_preferred_texture(
            resolved_refs.get("image_inventory", []),
            exclude_tokens=("_square_png.vtex_c",),
        )

    if entity_type == "sticker":
        return choose_preferred_texture(
            resolved_refs.get("material", []),
            required_prefix="panorama/images/econ/stickers/",
            exclude_tokens=("_1355_37_png.vtex_c",),
        )

    if entity_type == "patch":
        return choose_preferred_texture(
            resolved_refs.get("material", []),
            required_prefix="panorama/images/econ/patches/",
        )

    if entity_type == "graffiti":
        path = choose_preferred_texture(
            resolved_refs.get("material", []),
            required_prefix="panorama/images/econ/stickers/",
        )
        if path is not None:
            return path
        return choose_preferred_texture(
            resolved_refs.get("material", []),
            required_prefix="materials/decals/sprays/",
            exclude_tokens=("_nodrips.vtex_c",),
        )

    return None


def choose_preferred_texture(
    paths: list[str],
    required_prefix: str | None = None,
    exclude_tokens: tuple[str, ...] = (),
) -> str | None:
    candidates = [
        path
        for path in paths
        if path.endswith(".vtex_c") and (required_prefix is None or path.startswith(required_prefix))
    ]
    if not candidates:
        return None

    filtered = [
        path
        for path in candidates
        if not any(token in path for token in exclude_tokens)
    ]
    if filtered:
        return filtered[0]
    return candidates[0]


def choose_available_tier(preview_images: dict[str, str], requested: str) -> str:
    if requested in preview_images:
        return requested
    for fallback in (requested, "light", "medium", "heavy"):
        if fallback in preview_images:
            return fallback
    return sorted(preview_images)[0]


def ensure_vrf_cli(root: Path) -> Path:
    asset_name = resolve_vrf_asset_name()
    cache_root = root / ".cache/tools/vrf-cli" / VRF_VERSION / asset_name.removesuffix(".zip")
    ensure_dir(cache_root)

    binary = find_vrf_cli_binary(cache_root)
    if binary is not None:
        return binary

    download_url = f"{VRF_RELEASE_BASE}/{asset_name}"
    archive_path = cache_root / asset_name
    request = urllib.request.Request(download_url, headers={"User-Agent": "cs2-items-api"})
    with urllib.request.urlopen(request) as response, archive_path.open("wb") as handle:
        shutil.copyfileobj(response, handle)

    with zipfile.ZipFile(archive_path) as bundle:
        bundle.extractall(cache_root)

    binary = find_vrf_cli_binary(cache_root)
    if binary is None:
        raise RuntimeError(f"Unable to locate Source2Viewer-CLI after extracting {asset_name}")

    if os.name != "nt":
        current_mode = binary.stat().st_mode
        binary.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return binary


def resolve_vrf_asset_name() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    asset_name = VRF_ASSETS.get((system, machine))
    if asset_name is None:
        raise RuntimeError(f"Unsupported platform for VRF CLI bootstrap: {platform.system()} {platform.machine()}")
    return asset_name


def find_vrf_cli_binary(root: Path) -> Path | None:
    candidates = (
        "Source2Viewer-CLI",
        "Source2Viewer-CLI.exe",
        "Source2Viewer.exe",
    )
    for candidate in candidates:
        path = root / candidate
        if path.exists():
            return path
    return None


def run_vrf_texture_export(vrf_cli: Path, input_root: Path, output_root: Path) -> None:
    threads = max(1, min(os.cpu_count() or 1, 8))
    command = [
        str(vrf_cli),
        "-i",
        str(input_root),
        "-o",
        str(output_root),
        "-d",
        "--recursive",
        "--threads",
        str(threads),
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
