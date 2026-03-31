from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import vdf

from cs2_skins_api.constants import APP_ID, DEFAULT_STEAM_ROOTS, GAME_INSTALLDIR, GAME_VPK_PATH
from cs2_skins_api.utils import md5_file, parse_int


@dataclass(slots=True)
class SteamInstall:
    library_path: Path
    steam_root: Path
    game_root: Path
    appmanifest_path: Path
    app_state: dict[str, Any]

    @property
    def build_id(self) -> str | None:
        return self.app_state.get("buildid")

    @property
    def target_build_id(self) -> str | None:
        return self.app_state.get("TargetBuildID") or self.app_state.get("targetbuildid")

    @property
    def last_updated(self) -> int | None:
        return parse_int(self.app_state.get("LastUpdated") or self.app_state.get("lastupdated"))

    @property
    def pak_path(self) -> Path:
        return self.game_root / GAME_VPK_PATH


def _load_vdf(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        loaded = vdf.load(handle)
    return loaded if isinstance(loaded, dict) else {}


def _extract_library_paths(steam_root: Path) -> list[Path]:
    library_paths = [steam_root]
    library_file = steam_root / "steamapps/libraryfolders.vdf"
    if not library_file.exists():
        return library_paths

    raw = _load_vdf(library_file)
    folders = raw.get("libraryfolders", raw)
    if not isinstance(folders, dict):
        return library_paths

    for value in folders.values():
        if not isinstance(value, dict):
            continue
        path_value = value.get("path")
        if not path_value:
            continue
        library_paths.append(Path(str(path_value)))

    deduped: list[Path] = []
    seen = set()
    for candidate in library_paths:
        candidate = candidate.expanduser()
        marker = str(candidate.resolve()) if candidate.exists() else str(candidate)
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(candidate)
    return deduped


def _normalize_game_root(custom_path: Path) -> Path:
    custom_path = custom_path.expanduser().resolve()
    if custom_path.is_file() and custom_path.name == "pak01_dir.vpk":
        return custom_path.parents[2]
    if (custom_path / GAME_VPK_PATH).exists():
        return custom_path
    if custom_path.name == "csgo" and (custom_path / "pak01_dir.vpk").exists():
        return custom_path.parents[1]
    if custom_path.name == "game" and (custom_path / "csgo/pak01_dir.vpk").exists():
        return custom_path.parent
    if custom_path.name == GAME_INSTALLDIR and (custom_path / GAME_VPK_PATH).exists():
        return custom_path
    steamapps_candidate = custom_path / "steamapps/common" / GAME_INSTALLDIR
    if (steamapps_candidate / GAME_VPK_PATH).exists():
        return steamapps_candidate
    raise FileNotFoundError(
        f"Unable to normalize game path from {custom_path}. Expected either the game root or a path ending in game/csgo."
    )


def _install_from_game_root(game_root: Path) -> SteamInstall:
    steamapps_path = game_root.parents[1]
    library_path = game_root.parents[2]
    appmanifest_path = steamapps_path / f"appmanifest_{APP_ID}.acf"
    if not appmanifest_path.exists():
        raise FileNotFoundError(f"Missing {appmanifest_path}")
    app_state = _load_vdf(appmanifest_path).get("AppState", {})
    if not isinstance(app_state, dict):
        raise ValueError(f"Malformed appmanifest: {appmanifest_path}")
    steam_root = library_path
    return SteamInstall(
        library_path=library_path,
        steam_root=steam_root,
        game_root=game_root,
        appmanifest_path=appmanifest_path,
        app_state=app_state,
    )


def discover_install(custom_game_path: str | None = None) -> SteamInstall:
    if custom_game_path:
        return _install_from_game_root(_normalize_game_root(Path(custom_game_path)))

    installs: list[SteamInstall] = []
    for steam_root in DEFAULT_STEAM_ROOTS:
        if not steam_root.exists():
            continue
        for library_path in _extract_library_paths(steam_root):
            appmanifest = library_path / "steamapps" / f"appmanifest_{APP_ID}.acf"
            game_root = library_path / "steamapps/common" / GAME_INSTALLDIR
            if not appmanifest.exists() or not (game_root / GAME_VPK_PATH).exists():
                continue
            app_state = _load_vdf(appmanifest).get("AppState", {})
            if not isinstance(app_state, dict):
                continue
            installs.append(
                SteamInstall(
                    library_path=library_path,
                    steam_root=steam_root,
                    game_root=game_root,
                    appmanifest_path=appmanifest,
                    app_state=app_state,
                )
            )

    if not installs:
        raise FileNotFoundError("Unable to locate a CS2 installation in known Steam library paths.")

    installs.sort(key=lambda install: install.last_updated or 0, reverse=True)
    return installs[0]


def collect_build_metadata(install: SteamInstall) -> dict[str, Any]:
    installed_depots = install.app_state.get("InstalledDepots", {})
    pak_path = install.pak_path
    return {
        "app_id": APP_ID,
        "build_id": install.build_id,
        "target_build_id": install.target_build_id,
        "last_updated": install.last_updated,
        "pak_md5": md5_file(pak_path),
        "pak_size": pak_path.stat().st_size,
        "installed_depots": installed_depots,
    }
