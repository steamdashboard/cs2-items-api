# Update Pipeline

## `make check-update`

1. Discover Steam libraries
2. Find CS2 installation
3. Read `appmanifest_730.acf`
4. Read `pak01_dir.vpk` file fingerprint
5. Compare against the last generated snapshot in `data/source/steam/build.json`

## `make update`

1. Repeat build detection
2. Open `pak01_dir.vpk`
3. Extract `scripts/items/items_game.txt`
4. Extract all `resource/csgo_*.txt`
5. Parse VDF
6. Resolve prefab inheritance
7. Write `data/source`
8. Write normalized `data/core`
9. Write derived `data/api`
10. Write `data/reports`
11. Compute a lightweight diff report against the previous generated API

## Unknown Handling

The builder reports:

- top-level blocks that are not handled explicitly
- prefabs that remain unclassified for API derivation
- containers whose drop graph cannot be resolved confidently

Policies:

- `prompt`: ask before continuing in interactive mode
- `raw`: continue and emit reports
- `fail`: abort generation

