from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import vdf
import vpk

from cs2_skins_api.assets import resolve_assets
from cs2_skins_api.constants import ITEMS_GAME_PATH, LOCALE_PREFIX, LOCALE_SUFFIX
from cs2_skins_api.consumer import build_consumer_dataset
from cs2_skins_api.normalize import Localizer, build_core_dataset, derive_api_dataset
from cs2_skins_api.rendered_media import build_rendered_media
from cs2_skins_api.steam import collect_build_metadata, discover_install
from cs2_skins_api.utils import decode_utf8, encode_path_key, ensure_dir, reset_dir, write_json, write_text


def output_root(cwd: Path | None = None) -> Path:
    return (cwd or Path.cwd()).resolve()


def load_previous_snapshot(root: Path) -> dict[str, Any] | None:
    build_path = root / "data/source/steam/build.json"
    if not build_path.exists():
        return None
    with build_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def check_update(custom_game_path: str | None = None, root: Path | None = None) -> dict[str, Any]:
    project_root = output_root(root)
    install = discover_install(custom_game_path)
    build_meta = collect_build_metadata(install)
    previous = load_previous_snapshot(project_root)

    if previous is None:
        status = "missing-local-snapshot"
    elif previous.get("build_id") != build_meta.get("build_id") or previous.get("pak_md5") != build_meta.get("pak_md5"):
        status = "update-available"
    else:
        status = "up-to-date"

    return {
        "status": status,
        "current": build_meta,
        "previous": previous,
    }


def run_update(
    custom_game_path: str | None = None,
    root: Path | None = None,
    unknown_policy: str = "prompt",
    asset_mode: str = "manifest",
    render_mode: str = "png",
) -> dict[str, Any]:
    project_root = output_root(root)
    previous_state = capture_previous_state(project_root)
    install = discover_install(custom_game_path)
    build_meta = collect_build_metadata(install)

    items_game_text, items_game, locales_raw, locale_tokens = extract_game_data(install)
    localizer = Localizer(locale_tokens)
    core = build_core_dataset(items_game, localizer)
    api = derive_api_dataset(core, localizer)
    reset_dir(project_root / "data/source/assets")
    api["assets"], asset_files, asset_stats, unresolved_assets = resolve_assets(
        pak_path=install.pak_path,
        api_assets=api["assets"],
        root=project_root,
        mode=asset_mode,
    )
    rendered = build_rendered_media(
        pak_path=install.pak_path,
        api_assets=api["assets"],
        skins=api["skins"],
        skin_variants=api["skin_variants"],
        root=project_root,
        mode=render_mode,
    )
    consumer = build_consumer_dataset(core, api, localizer, rendered)

    issues = {
        "unknown_blocks": core["reports"]["unknown_blocks"],
        "unknown_prefabs": core["reports"]["unknown_prefabs"],
        "unresolved_containers": api["reports"]["unresolved_containers"],
    }
    maybe_handle_issues(issues, unknown_policy)

    generated_at = datetime.now(timezone.utc).isoformat()
    write_source_layer(project_root, build_meta, items_game_text, locales_raw, generated_at)
    write_asset_source_layer(project_root, asset_files, asset_stats, unresolved_assets, generated_at)
    write_core_layer(project_root, core, locale_tokens)
    write_api_layer(
        project_root,
        core,
        api,
        consumer,
        rendered,
        build_meta,
        generated_at,
        asset_files,
        asset_stats,
        unresolved_assets,
    )
    write_reports(project_root, core, api, previous_state, generated_at)

    return {
        "build": build_meta,
        "generated_at": generated_at,
        "stats": build_stats(core, api, consumer, rendered),
    }


def capture_previous_state(root: Path) -> dict[str, list[str]]:
    state: dict[str, list[str]] = {}
    for entity_name in (
        "finishes",
        "skins",
        "skin-variants",
        "collections",
        "collectibles",
        "containers",
        "equipment",
        "stickers",
        "patches",
        "graffiti",
        "special-drops",
        "tournaments",
        "teams",
        "players",
        "assets",
        "sticker-capsules",
        "agents",
        "charms",
        "music-kits",
        "weapons",
        "tools",
    ):
        if entity_name == "assets":
            directory = root / "data/api" / "media" / "manifests"
        else:
            directory = root / "data/api" / "reference" / entity_name
        if not directory.exists():
            directory = root / "data/api" / entity_name
        if not directory.exists():
            state[entity_name] = []
            continue
        state[entity_name] = sorted(path.stem for path in directory.glob("*.json"))
    return state


def extract_game_data(install) -> tuple[str, dict[str, Any], dict[str, str], dict[str, dict[str, str]]]:
    archive = vpk.open(str(install.pak_path))
    items_game_text = decode_utf8(archive.get_file(ITEMS_GAME_PATH).read())
    items_game = vdf.loads(items_game_text).get("items_game", {})

    locales_raw = {}
    locale_tokens = {}
    for path in archive:
        if not path.startswith(LOCALE_PREFIX) or not path.endswith(LOCALE_SUFFIX):
            continue
        locale_text = decode_utf8(archive.get_file(path).read())
        locale_name = path[len(LOCALE_PREFIX) : -len(LOCALE_SUFFIX)]
        locales_raw[locale_name] = locale_text
        locale_tokens[locale_name] = (
            vdf.loads(locale_text)
            .get("lang", {})
            .get("Tokens", {})
        )
    return items_game_text, items_game, locales_raw, locale_tokens


def maybe_handle_issues(issues: dict[str, Any], unknown_policy: str) -> None:
    has_issues = any(issues.values())
    if not has_issues:
        return
    if unknown_policy == "raw":
        return
    if unknown_policy == "fail":
        raise RuntimeError("Unknown or unresolved classes were detected. See data/reports after a raw run.")
    if unknown_policy == "prompt" and sys.stdin.isatty():
        print("Unknown or unresolved classes were detected.")
        for key, value in issues.items():
            if value:
                if isinstance(value, list):
                    print(f"- {key}: {len(value)}")
                else:
                    print(f"- {key}: present")
        answer = input("Continue and emit raw reports? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            raise RuntimeError("Update aborted by user.")


def write_source_layer(
    root: Path,
    build_meta: dict[str, Any],
    items_game_text: str,
    locales_raw: dict[str, str],
    generated_at: str,
) -> None:
    source_root = root / "data/source"
    reset_dir(source_root / "steam")
    reset_dir(source_root / "raw")
    reset_dir(source_root / "raw/locales")

    write_json(source_root / "steam/build.json", {**build_meta, "generated_at": generated_at})
    write_text(source_root / "raw/items_game.txt", items_game_text)
    for locale_name, locale_text in sorted(locales_raw.items()):
        write_text(source_root / "raw/locales" / f"csgo_{locale_name}.txt", locale_text)


def write_asset_source_layer(
    root: Path,
    asset_files: dict[str, Any],
    asset_stats: dict[str, Any],
    unresolved_assets: list[dict[str, Any]],
    generated_at: str,
) -> None:
    asset_root = root / "data/source/assets"
    asset_root.mkdir(parents=True, exist_ok=True)
    write_json(asset_root / "files.json", asset_files)
    write_json(asset_root / "stats.json", {**asset_stats, "generated_at": generated_at})
    write_json(asset_root / "unresolved.json", unresolved_assets)


def write_core_layer(root: Path, core: dict[str, Any], locale_tokens: dict[str, dict[str, str]]) -> None:
    core_root = root / "data/core"
    reset_dir(core_root)

    for enum_name, payload in core["enums"].items():
        write_json(core_root / "enums" / f"{enum_name}.json", payload)

    for prefab_id, payload in sorted(core["prefabs"].items()):
        write_json(core_root / "prefabs" / f"{prefab_id}.json", payload)

    for item_id, payload in sorted(core["resolved_items"].items(), key=lambda pair: pair[0]):
        write_json(core_root / "item-definitions" / f"{payload['id']}.json", payload)

    for paint_kit_id, payload in sorted(core["paint_kits"].items(), key=lambda pair: int(pair[0])):
        write_json(core_root / "paint-kits" / f"{payload['id']}.json", payload)

    for sticker_kit_id, payload in sorted(core["sticker_kits"].items(), key=lambda pair: int(pair[0])):
        write_json(core_root / "sticker-kits" / f"{payload['id']}.json", payload)

    for item_set_id, payload in sorted(core["item_sets"].items()):
        write_json(core_root / "item-sets" / f"{item_set_id}.json", payload)

    for loot_list_id, payload in sorted(core["loot_lists"].items()):
        write_json(core_root / "loot-lists" / f"{loot_list_id}.json", payload)

    for keychain_id, payload in sorted(core["keychains"].items(), key=lambda pair: int(pair[0])):
        write_json(core_root / "keychains" / f"{payload['id']}.json", payload)

    for music_id, payload in sorted(core["music_definitions"].items(), key=lambda pair: int(pair[0])):
        write_json(core_root / "music-definitions" / f"{payload['id']}.json", payload)

    for locale_name, tokens in sorted(locale_tokens.items()):
        write_json(core_root / "locales" / f"tokens.{locale_name}.json", tokens)

    write_json(core_root / "tournaments" / "pro-event-results.json", core["raw"]["pro_event_results"])
    write_json(core_root / "pro-players" / "index.json", core["raw"]["pro_players"])
    write_json(core_root / "pro-teams" / "index.json", core["raw"]["pro_teams"])


def write_api_layer(
    root: Path,
    core: dict[str, Any],
    api: dict[str, Any],
    consumer: dict[str, Any],
    rendered: dict[str, Any],
    build_meta: dict[str, Any],
    generated_at: str,
    asset_files: dict[str, Any],
    asset_stats: dict[str, Any],
    unresolved_assets: list[dict[str, Any]],
) -> None:
    api_root = root / "data/api"
    reset_dir(api_root)

    reference_root = api_root / "reference"
    write_entity_group(reference_root / "finishes", api["finishes"])
    write_entity_group(reference_root / "weapons", api["weapons"])
    write_entity_group(reference_root / "collections", api["collections"])
    write_entity_group(reference_root / "collectibles", api["collectibles"])
    write_entity_group(reference_root / "containers", api["containers"])
    write_entity_group(reference_root / "equipment", api["equipment"])
    write_entity_group(reference_root / "skins", api["skins"])
    write_entity_group(reference_root / "skin-variants", api["skin_variants"])
    write_entity_group(reference_root / "stickers", api["stickers"])
    write_entity_group(reference_root / "patches", api["patches"])
    write_entity_group(reference_root / "graffiti", api["graffiti"])
    write_entity_group(reference_root / "special-drops", api["special_drops"])
    write_entity_group(reference_root / "tournaments", api["tournaments"])
    write_entity_group(reference_root / "teams", api["teams"])
    write_entity_group(reference_root / "players", api["players"])
    write_entity_group(reference_root / "sticker-capsules", api["sticker_capsules"])
    write_entity_group(reference_root / "agents", api["agents"])
    write_entity_group(reference_root / "charms", api["charms"])
    write_entity_group(reference_root / "music-kits", api["music_kits"])
    write_entity_group(reference_root / "tools", api["tools"])

    graph_root = api_root / "graph"
    for relation_name, payload in api["relations"].items():
        write_json(graph_root / "relations" / f"{relation_name}.json", payload)

    write_indexes(graph_root / "indexes", api["indexes"])

    media_root = api_root / "media"
    write_entity_group(media_root / "manifests", api["assets"])
    write_json(media_root / "files.json", asset_files)
    write_json(media_root / "stats.json", {**asset_stats, "generated_at": generated_at})
    write_json(media_root / "unresolved.json", unresolved_assets)
    for folder_name, payload in rendered["entities"].items():
        write_entity_group(media_root / "rendered" / "manifests" / folder_name, payload)
    write_entity_group(media_root / "rendered" / "manifests" / "skins", rendered["skins"])
    write_entity_group(media_root / "rendered" / "manifests" / "skin-variants", rendered["skin_variants"])
    write_json(media_root / "rendered" / "stats.json", {**rendered["stats"], "generated_at": generated_at})
    write_json(media_root / "rendered" / "unresolved.json", rendered["unresolved"])
    for relative_path, staged_source in sorted(rendered["staged_files"].items()):
        target = root / relative_path
        ensure_dir(target.parent)
        Path(target).write_bytes(Path(staged_source).read_bytes())

    consumer_root = api_root / "consumer"
    for group_name, payload in consumer["cards"].items():
        write_entity_group(consumer_root / "cards" / group_name, payload)
    for group_name, payload in consumer.get("overlays", {}).items():
        write_entity_group(consumer_root / "overlays" / group_name, payload)
    write_consumer_indexes(consumer_root / "lists", consumer["lists"])
    for browse_name, payload in consumer["browse"].items():
        write_json(consumer_root / "browse" / f"{browse_name}.json", payload)
    write_json(
        consumer_root / "meta" / "schema.json",
        {
            "generated_at": generated_at,
            "cards": {
                group_name: f"data/api/consumer/cards/{group_name}/<id>.json"
                for group_name in sorted(consumer["cards"])
            },
            "overlays": {
                group_name: f"data/api/consumer/overlays/{group_name}/<id>.json"
                for group_name in sorted(consumer.get("overlays", {}))
            },
            "lists": {
                list_name: f"data/api/consumer/lists/{list_name}/<key>.json"
                for list_name in sorted(consumer["lists"])
            },
            "browse": {
                browse_name: f"data/api/consumer/browse/{browse_name}.json"
                for browse_name in sorted(consumer["browse"])
            },
        },
    )
    write_json(consumer_root / "meta" / "discovery.json", consumer["meta"]["discovery"])
    write_json(consumer_root / "meta" / "facets.json", consumer["meta"]["facets"])

    schema = {
        "version": 10,
        "generated_at": generated_at,
        "layers": {
            "reference": "Canonical normalized entities and stable IDs.",
            "graph": "Machine-oriented relations and lookup indexes.",
            "consumer": "Human-oriented cards, trading overlays, browse entrypoints, and ready-made lists.",
            "media": "Resolved asset manifests, rendered previews, and asset file coverage.",
        },
        "layout": {
            "reference": {
                "finishes": "data/api/reference/finishes/<paint_kit_id>.json",
                "weapons": "data/api/reference/weapons/<item_definition_id>.json",
                "skins": "data/api/reference/skins/<weapon_id>-<paint_kit_id>.json",
                "skin_variants": "data/api/reference/skin-variants/<skin_id>__<quality>__<exterior>.json",
                "collections": "data/api/reference/collections/<item_set_id>.json",
                "collectibles": "data/api/reference/collectibles/<item_definition_id>.json",
                "containers": "data/api/reference/containers/<item_definition_id>.json",
                "equipment": "data/api/reference/equipment/<item_definition_id>.json",
                "stickers": "data/api/reference/stickers/<sticker_kit_id>.json",
                "patches": "data/api/reference/patches/<sticker_kit_id>.json",
                "graffiti": "data/api/reference/graffiti/<sticker_kit_id>.json",
                "special_drops": "data/api/reference/special-drops/<token>.json",
                "tournaments": "data/api/reference/tournaments/<event_id>.json",
                "teams": "data/api/reference/teams/<team_id>.json",
                "players": "data/api/reference/players/<player_id>.json",
                "sticker_capsules": "data/api/reference/sticker-capsules/<container_id>.json",
                "agents": "data/api/reference/agents/<item_definition_id>.json",
                "charms": "data/api/reference/charms/<keychain_definition_id>.json",
                "music_kits": "data/api/reference/music-kits/<music_definition_id>.json",
                "tools": "data/api/reference/tools/<item_definition_id>.json",
            },
            "graph": {
                "relations": "data/api/graph/relations/<relation>.json",
                "indexes": "data/api/graph/indexes/<index>/<key>.json",
            },
            "consumer": {
                "cards": "data/api/consumer/cards/<group>/<id>.json",
                "overlays": "data/api/consumer/overlays/<group>/<id>.json",
                "lists": "data/api/consumer/lists/<list>/<key>.json",
                "browse": "data/api/consumer/browse/<entrypoint>.json",
                "meta": "data/api/consumer/meta/<file>.json",
            },
            "media": {
                "manifests": "data/api/media/manifests/<entity_type>__<entity_id>.json",
                "files": "data/api/media/files.json",
                "stats": "data/api/media/stats.json",
                "unresolved": "data/api/media/unresolved.json",
                "rendered_entity_manifests": "data/api/media/rendered/manifests/<entity_group>/<id>.json",
                "rendered_skin_manifests": "data/api/media/rendered/manifests/skins/<skin_id>.json",
                "rendered_skin_variant_manifests": "data/api/media/rendered/manifests/skin-variants/<variant_id>.json",
                "rendered_files": "data/api/media/rendered/files/<entity_group>/<id>/<name>.png",
                "rendered_stats": "data/api/media/rendered/stats.json",
                "rendered_unresolved": "data/api/media/rendered/unresolved.json",
            },
        },
        "id_policy": {
            "skin": "<weapon_id>-<paint_kit_id>",
            "skin_variant": "<skin_id>__<quality>__<exterior>",
        },
        "slug_policy": {
            "canonical_slug": "slug(codename) when codename exists, otherwise slug(id); stable alias layer and not guaranteed unique across kinds.",
            "search_slug": "slug(human-readable name or market hash name); search-friendly layer and not a stable identity contract.",
        },
    }
    stats = build_stats(core, api, consumer, rendered)
    write_json(api_root / "meta" / "schema.json", schema)
    write_json(api_root / "meta" / "build.json", {**build_meta, "generated_at": generated_at})
    write_json(api_root / "meta" / "stats.json", stats)


def write_entity_group(directory: Path, payload: dict[str, Any]) -> None:
    for entity_id, entity in payload.items():
        write_json(directory / f"{entity_id}.json", entity)


def write_indexes(index_root: Path, indexes: dict[str, Any]) -> None:
    for index_name, payload in indexes.items():
        directory = index_root / index_name
        for key, value in payload.items():
            write_json(directory / f"{encode_path_key(key)}.json", {"key": key, "items": value})


def write_consumer_indexes(index_root: Path, indexes: dict[str, Any]) -> None:
    for index_name, payload in indexes.items():
        directory = index_root / index_name
        for key, value in payload.items():
            if isinstance(value, list):
                body = {"key": key, "items": value}
            elif isinstance(value, dict):
                body = {"key": key, **value}
            else:
                body = {"key": key, "value": value}
            write_json(directory / f"{encode_path_key(key)}.json", body)


def write_reports(
    root: Path,
    core: dict[str, Any],
    api: dict[str, Any],
    previous_state: dict[str, list[str]],
    generated_at: str,
) -> None:
    reports_root = root / "data/reports"
    reset_dir(reports_root)

    current_state = {
        "finishes": sorted(str(key) for key in api["finishes"].keys()),
        "skins": sorted(api["skins"].keys()),
        "skin-variants": sorted(api["skin_variants"].keys()),
        "collections": sorted(api["collections"].keys()),
        "collectibles": sorted(str(key) for key in api["collectibles"].keys()),
        "containers": sorted(str(key) for key in api["containers"].keys()),
        "equipment": sorted(str(key) for key in api["equipment"].keys()),
        "stickers": sorted(str(key) for key in api["stickers"].keys()),
        "patches": sorted(str(key) for key in api["patches"].keys()),
        "graffiti": sorted(str(key) for key in api["graffiti"].keys()),
        "special-drops": sorted(str(key) for key in api["special_drops"].keys()),
        "tournaments": sorted(str(key) for key in api["tournaments"].keys()),
        "teams": sorted(str(key) for key in api["teams"].keys()),
        "players": sorted(str(key) for key in api["players"].keys()),
        "assets": sorted(str(key) for key in api["assets"].keys()),
        "sticker-capsules": sorted(str(key) for key in api["sticker_capsules"].keys()),
        "agents": sorted(str(key) for key in api["agents"].keys()),
        "charms": sorted(str(key) for key in api["charms"].keys()),
        "music-kits": sorted(str(key) for key in api["music_kits"].keys()),
        "weapons": sorted(str(key) for key in api["weapons"].keys()),
        "tools": sorted(str(key) for key in api["tools"].keys()),
    }

    diff = {}
    for entity_name, current_ids in current_state.items():
        previous_ids = set(previous_state.get(entity_name, []))
        current_set = set(current_ids)
        diff[entity_name] = {
            "added": sorted(current_set - previous_ids),
            "removed": sorted(previous_ids - current_set),
            "count": len(current_ids),
        }

    write_json(reports_root / "latest-diff.json", {"generated_at": generated_at, "entities": diff})
    write_json(reports_root / "unknown-blocks.json", core["reports"]["unknown_blocks"])
    write_json(reports_root / "unknown-prefabs.json", core["reports"]["unknown_prefabs"])
    write_json(reports_root / "unresolved-containers.json", api["reports"]["unresolved_containers"])


def build_stats(
    core: dict[str, Any],
    api: dict[str, Any],
    consumer: dict[str, Any],
    rendered: dict[str, Any],
) -> dict[str, Any]:
    stats = {
        "finishes": len(api["finishes"]),
        "weapons": len(api["weapons"]),
        "collections": len(api["collections"]),
        "collectibles": len(api["collectibles"]),
        "containers": len(api["containers"]),
        "equipment": len(api["equipment"]),
        "skins": len(api["skins"]),
        "skin_variants": len(api["skin_variants"]),
        "stickers": len(api["stickers"]),
        "patches": len(api["patches"]),
        "graffiti": len(api["graffiti"]),
        "special_drops": len(api["special_drops"]),
        "tournaments": len(api["tournaments"]),
        "teams": len(api["teams"]),
        "players": len(api["players"]),
        "assets": len(api["assets"]),
        "sticker_capsules": len(api["sticker_capsules"]),
        "agents": len(api["agents"]),
        "charms": len(api["charms"]),
        "music_kits": len(api["music_kits"]),
        "tools": len(api["tools"]),
        "unknown_blocks": len(core.get("reports", {}).get("unknown_blocks", [])),
        "unknown_prefabs": len(core.get("reports", {}).get("unknown_prefabs", [])),
        "unresolved_containers": len(api.get("reports", {}).get("unresolved_containers", [])),
        "rendered.skins": len(rendered.get("skins", {})),
        "rendered.skin_variants": len(rendered.get("skin_variants", {})),
    }
    for group_name, count in consumer.get("stats", {}).items():
        stats[f"consumer.{group_name}"] = count
    for stat_name, value in rendered.get("stats", {}).items():
        stats[f"rendered.{stat_name}"] = value
    return stats
