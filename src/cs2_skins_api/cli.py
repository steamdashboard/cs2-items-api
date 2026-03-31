from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from cs2_skins_api.build import check_update, run_update


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cs2-items-api")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check-update", help="Check whether the local game build differs from the generated snapshot.")
    check_parser.add_argument("--game-path", default=os.environ.get("CS2_GAME_PATH"))

    update_parser = subparsers.add_parser("update", help="Extract game data and rebuild the repository output.")
    update_parser.add_argument("--game-path", default=os.environ.get("CS2_GAME_PATH"))
    update_parser.add_argument(
        "--unknown-policy",
        default=os.environ.get("CS2_UNKNOWN_POLICY", "prompt"),
        choices=("prompt", "raw", "fail"),
    )
    update_parser.add_argument(
        "--asset-mode",
        default=os.environ.get("CS2_ASSET_MODE", "manifest"),
        choices=("manifest", "extract"),
    )
    update_parser.add_argument(
        "--render-mode",
        default=os.environ.get("CS2_RENDER_MODE", "png"),
        choices=("none", "png"),
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "check-update":
        payload = check_update(custom_game_path=args.game_path, root=Path.cwd())
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if args.command == "update":
        payload = run_update(
            custom_game_path=args.game_path,
            root=Path.cwd(),
            unknown_policy=args.unknown_policy,
            asset_mode=args.asset_mode,
            render_mode=args.render_mode,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2
