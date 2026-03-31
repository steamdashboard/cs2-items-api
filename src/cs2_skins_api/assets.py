from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import vpk

from cs2_skins_api.utils import ensure_dir


IMAGE_PATH_SUFFIXES = (
    "_png.vtex_c",
    "_store_png.vtex_c",
    "_double_store_png.vtex_c",
    "_square_png.vtex_c",
    "_large_png.vtex_c",
    "_1355_37_png.vtex_c",
)

MODEL_REF_KEYS = {
    "model_player",
    "model_world",
    "model_ag2",
    "pedestal_display_model",
    "inventory_image_data.root_mdl",
}


def resolve_assets(
    pak_path: Path,
    api_assets: dict[str, dict[str, Any]],
    root: Path,
    mode: str = "manifest",
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    archive = vpk.open(str(pak_path))
    archive_paths = set(archive)

    resolved_assets: dict[str, dict[str, Any]] = {}
    unique_files: dict[str, dict[str, Any]] = {}
    unresolved: list[dict[str, Any]] = []
    stats = Counter()

    extract_root = root / "data/source/assets/files"
    if mode == "extract":
        ensure_dir(extract_root)

    for asset_id, asset in api_assets.items():
        refs = dict(asset.get("refs", {}))
        if isinstance(refs.get("inventory_image_data"), dict):
            root_mdl = refs["inventory_image_data"].get("root_mdl")
            if root_mdl:
                refs["inventory_image_data.root_mdl"] = root_mdl

        resolved_refs: dict[str, list[str]] = {}
        unresolved_refs: list[str] = []
        stats["asset_entities"] += 1

        for ref_key, ref_value in refs.items():
            stats["asset_refs"] += 1
            if ref_key in {"image_inventory_size", "inventory_image_data", "display_seed", "inventory_image_section"}:
                continue

            matches = []
            for candidate in candidate_paths(asset["entity_type"], ref_key, ref_value):
                if candidate not in archive_paths:
                    continue
                file_record = unique_files.get(candidate)
                if file_record is None:
                    file_record = build_file_record(archive, candidate)
                    if mode == "extract":
                        file_record["extracted_path"] = extract_asset_file(archive, candidate, extract_root)
                    unique_files[candidate] = file_record
                    stats["unique_asset_files"] += 1
                    stats[f"unique_asset_files.{file_record['kind']}"] += 1
                    if mode == "extract":
                        stats["extracted_asset_files"] += 1
                matches.append(candidate)

            if matches:
                resolved_refs[ref_key] = matches
                stats["resolved_asset_refs"] += 1
            else:
                unresolved_refs.append(ref_key)
                stats["unresolved_asset_refs"] += 1

        enriched = {
            **asset,
            "resolved_refs": resolved_refs,
            "unresolved_refs": sorted(unresolved_refs),
        }
        if resolved_refs:
            stats["asset_entities_with_files"] += 1
        else:
            stats["asset_entities_without_files"] += 1
        if unresolved_refs:
            unresolved.append(
                {
                    "asset_id": asset_id,
                    "entity_type": asset["entity_type"],
                    "entity_id": asset["entity_id"],
                    "name": asset["name"],
                    "unresolved_refs": sorted(unresolved_refs),
                }
            )
        resolved_assets[asset_id] = enriched

    files_index = {
        "files": unique_files,
    }
    stats_payload = {
        "mode": mode,
        **dict(stats),
    }
    return resolved_assets, files_index, stats_payload, sorted(unresolved, key=lambda row: row["asset_id"])


def candidate_paths(entity_type: str, ref_key: str, ref_value: Any) -> list[str]:
    value = str(ref_value).strip().strip("/")
    if not value:
        return []

    if ref_key in {"image_inventory", "image_unusual_item"}:
        return [f"panorama/images/{value}{suffix}" for suffix in IMAGE_PATH_SUFFIXES]

    if ref_key in MODEL_REF_KEYS:
        paths = [compiled_resource_path(value), value]
        basename = Path(value).name
        if basename.endswith(".vmdl"):
            paths.append(f"characters/models/shared/animsets/{basename}_c")
        return dedupe(paths)

    if ref_key == "icon_default_image":
        if value.endswith(".vtf"):
            return [value[:-4] + ".vtex_c", value]
        return [value]

    if ref_key == "material":
        paths = [
            f"stickers/{value}.vmat_c",
            f"patches/{value}.vmat_c",
            f"materials/decals/sprays/{value}.vtex_c",
            f"materials/decals/sprays/{value}_nodrips.vtex_c",
        ]
        for prefix in ("panorama/images/econ/stickers", "panorama/images/econ/patches"):
            for suffix in ("_png.vtex_c", "_1355_37_png.vtex_c"):
                paths.append(f"{prefix}/{value}{suffix}")
        return dedupe(paths)

    return []


def compiled_resource_path(value: str) -> str:
    if value.endswith("_c"):
        return value
    if value.endswith(".vmdl"):
        return value + "_c"
    if value.endswith(".vmat"):
        return value + "_c"
    return value + "_c"


def build_file_record(archive: vpk.VPK, path: str) -> dict[str, Any]:
    file = archive.get_file(path)
    return {
        "path": path,
        "kind": infer_file_kind(path),
        "archive_index": file.archive_index,
        "crc32": file.crc32,
        "size": getattr(file, "file_length", None) or getattr(file, "length", None),
    }


def infer_file_kind(path: str) -> str:
    if path.endswith(".vmdl_c"):
        return "model"
    if path.endswith(".vmat_c"):
        return "material"
    if path.endswith(".vtex_c"):
        return "texture"
    return "file"


def extract_asset_file(archive: vpk.VPK, vpk_path: str, root: Path) -> str:
    target = root / vpk_path
    ensure_dir(target.parent)
    target.write_bytes(archive.get_file(vpk_path).read())
    return str(target.relative_to(root.parents[3]))


def dedupe(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output
