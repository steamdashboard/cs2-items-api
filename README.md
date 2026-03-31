# cs2-items-api

`cs2-items-api` builds a file-based CS2 data API directly from installed game files.

The repository is meant to be committed as data, then consumed over `raw.githubusercontent.com` or any other Git hosting raw endpoint.

## Positioning

The project is positioned as `cs2-items-api` because the extracted dataset covers the broader CS2 item and cosmetic ecosystem, not just weapon finishes.

That includes:

- weapon skins
- knife skins
- gloves
- cases
- capsules
- souvenir packages
- stickers
- patches
- graffiti
- agents
- charms
- music kits
- tools and other game-backed economy items

The API still keeps precise names for the exported entities such as `cases`, `capsules`, `stickers`, `agents`, `charms`, `collections`, `weapons`, `skins`, and `skin variants`.

The internal Python module name remains `cs2_skins_api` for now to avoid a disruptive package rename, but the public project positioning is `cs2-items-api`.

## Scope

The builder reads `items_game.txt` and locale files from the installed CS2 VPK archives, normalizes them, and publishes source-backed API layers on top of the extracted sources:

- `data/source`: extracted game sources and Steam build metadata
- `data/core`: normalized game-native entities
- `data/api/reference`: canonical normalized entities
- `data/api/graph`: relations and machine-oriented lookup indexes
- `data/api/consumer`: human-oriented, but still strictly derived, cards and browse entrypoints
- `data/api/media`: resolved asset manifests, rendered skin previews, and asset coverage metadata

The first implementation focuses on:

- Steam / CS2 detection on Linux, macOS, and Windows-style default paths
- build checking via `appmanifest_730.acf` and `pak01_dir.vpk`
- extraction from `pak01_dir.vpk`
- prefab resolution
- core exports for items, paint kits, sticker kits, item sets, loot lists, music kits, keychains, locales
- reference exports for finishes, weapons, skins, skin variants, collections, containers, stickers, patches, graffiti, special drops, sticker capsules, tournaments, teams, players, agents, charms, music kits, and tools
- consumer exports for source-backed item pages, localized names, deterministic prebuilt lists, source-tier rarity summaries, and trading overlays for finish families, rare-pattern mechanics, phases, market constraints, and seed lookup overlays where the mechanic can be reproduced offline
- source asset manifests that resolve logical game refs to real VPK file paths
- rendered PNG previews with semantic file paths for skins, skin variants, weapons, containers, stickers, patches, graffiti, agents, charms, music kits, and tools
- reports for unknown blocks, unknown prefabs, and unresolved container sources
- contract validation for the generated API layout

This makes the repository a raw API and data backbone for downstream products such as:

- wiki-style item pages
- case and collection browsers
- skin databases
- market explorers
- media pipelines
- separate pricing and liquidity overlays that can still be added later without changing the extraction-first core

## Install

```bash
make install
```

This installs runtime dependencies into a local `.python_packages/` directory. A virtual environment is not required.

## Usage

Check whether the local game build differs from the last generated snapshot:

```bash
make check-update
```

Run a full extraction and rebuild:

```bash
make update
```

Validate the generated API contract without needing a local CS2 install:

```bash
make validate
```

Use a custom game path when needed:

```bash
make check-update GAME_PATH="/path/to/Counter-Strike Global Offensive"
make update GAME_PATH="/path/to/Counter-Strike Global Offensive"
```

Choose how unknown or unresolved classes are handled:

```bash
make update UNKNOWN_POLICY=fail
make update UNKNOWN_POLICY=raw
```

`UNKNOWN_POLICY=prompt` is the default. In an interactive shell the builder asks whether to continue when unresolved classes are found.

Choose how asset files are handled:

```bash
make update ASSET_MODE=manifest
make update ASSET_MODE=extract
```

`ASSET_MODE=manifest` is the default and records resolved VPK file paths and metadata in `data/source/assets/`.
`ASSET_MODE=extract` additionally writes the referenced compiled asset files under `data/source/assets/files/`.

Choose whether rendered skin preview images are generated:

```bash
make update RENDER_MODE=png
make update RENDER_MODE=none
```

`RENDER_MODE=png` is the default. On first use the builder bootstraps the pinned `Source2Viewer-CLI` release from the official `ValveResourceFormat` GitHub project into `.cache/tools/` and exports semantic PNG previews for every skin.

## Output Layout

```text
data/
  source/
  core/
  api/
    reference/
    graph/
    consumer/
    media/
    meta/
  reports/
```

Key entrypoints:

- `data/api/meta/schema.json`: API layer contract and path layout
- `data/api/meta/build.json`: public build metadata without local filesystem paths
- `data/api/reference/skins/<skin_id>.json`: canonical skin entity
- `data/api/reference/containers/<container_id>.json`: canonical container entity
- `data/api/graph/indexes/*`: raw lookup indexes
- `data/api/consumer/cards/skins/<skin_id>.json`: page-ready consumer skin card
- `data/api/consumer/cards/cases/<container_id>.json`: page-ready consumer case card
- `data/api/consumer/cards/special-pools/<token>.json`: consumer special item pool card
- `data/api/consumer/browse/finishes.json`: finish browse entrypoint backed by reference finishes
- `data/api/consumer/lists/by-rarity/<rarity>.json`: deterministic rarity list across consumer cards
- `data/api/consumer/overlays/finish-families/<family_id>.json`: trading-oriented finish-family overlay
- `data/api/consumer/overlays/rare-patterns/<mechanic_id>.json`: trading-oriented rare-pattern overlay
- `data/api/consumer/overlays/phases/<paint_kit_id>.json`: phase overlay keyed by finish
- `data/api/consumer/overlays/market-constraints/<constraint_id>.json`: market-state or tradability overlay
- `data/api/consumer/overlays/seed-lookups/<lookup_id>.json`: deterministic per-skin seed lookup overlay for supported mechanics
- `data/api/consumer/meta/discovery.json`: consumer entrypoints and counts
- `data/api/media/manifests/<entity_type>__<entity_id>.json`: resolved asset manifest
- `data/api/media/rendered/manifests/<entity_group>/<id>.json`: rendered entity preview manifest
- `data/api/media/rendered/manifests/skins/<skin_id>.json`: rendered skin preview manifest
- `data/api/media/rendered/manifests/skin-variants/<variant_id>.json`: rendered skin variant manifest
- `data/api/media/rendered/files/<entity_group>/<id>/<name>.png`: semantic PNG preview file

Consumer cards and overlays now carry deterministic expert-facing semantics where the game data supports them, including:

- source-backed or source-tier rarity summaries
- `resolution_level`, `deterministic_inputs`, and `seed_domain` for trading-sensitive finishes
- trade-up aware seed domains that distinguish the common `0..999` opening range from the full `0..1000` deterministic pattern space
- `float_relevance` and inspect-ready refs for skin variants
- native deterministic seed lookup overlays for supported Fade / Amber Fade / Acid Fade skins
- explicit media honesty fields such as `media_scope` and `coverage_status`

## Consuming Over Raw GitHub

The generated dataset can be consumed directly from GitHub raw URLs.

These examples assume the repository is public. For private repositories, `raw.githubusercontent.com` requires authenticated access through GitHub APIs or another authenticated distribution layer.

Base URLs:

- repository: `https://github.com/steamdashboard/cs2-items-api`
- raw root: `https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main`
- API root: `https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api`

If you need immutable responses, replace `main` with a commit SHA or tag instead of following the moving branch tip.

Useful raw URLs:

- schema: `https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/meta/schema.json`
- consumer discovery: `https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/consumer/meta/discovery.json`
- sample skin card: `https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/consumer/cards/skins/1-37.json`
- sample case card: `https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/consumer/cards/cases/4001.json`
- sample finish-family overlay: `https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/consumer/overlays/finish-families/case-hardened.json`
- sample rare-pattern overlay: `https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/consumer/overlays/rare-patterns/blue-gem.json`
- sample seed lookup overlay: `https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/consumer/overlays/seed-lookups/500-38__fade-percentage.json`
- sample finishes browse: `https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/consumer/browse/finishes.json`
- sample rarity list: `https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/consumer/lists/by-rarity/legendary.json`
- sample agent card: `https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/consumer/cards/agents/5505.json`
- sample collection card: `https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/consumer/cards/collections/set_anubis.json`
- sample skin variant: `https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/reference/skin-variants/1-37__normal__factory-new.json`
- sample canonical slug index: `https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/graph/indexes/by-canonical-slug/set-gamma-2.json`
- sample slug index: `https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/graph/indexes/by-slug/desert-eagle-blaze.json`
- sample market hash name index: `https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/graph/indexes/by-market-hash-name/Desert%20Eagle%20%7C%20Blaze%20%28Factory%20New%29.json`
- sample rendered PNG: `https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/media/rendered/files/skins/1-37/light.png`

Slug fields:

- `canonical_slug`: stable alias built from `codename` when present, otherwise from stable `id`
- `search_slug`: human-friendly slug built from display names or market names

### `curl`

Fetch the discovery document:

```bash
curl -L \
  https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/consumer/meta/discovery.json
```

Fetch a skin card:

```bash
curl -L \
  https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/consumer/cards/skins/1-37.json
```

Fetch a case card:

```bash
curl -L \
  https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/consumer/cards/cases/4001.json
```

Fetch an agent card:

```bash
curl -L \
  https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/consumer/cards/agents/5505.json
```

Fetch a collection card:

```bash
curl -L \
  https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/consumer/cards/collections/set_anubis.json
```

### JavaScript / TypeScript

```ts
const API_ROOT =
  "https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api";

const discovery = await fetch(`${API_ROOT}/consumer/meta/discovery.json`).then((res) =>
  res.json(),
);

const skin = await fetch(`${API_ROOT}/consumer/cards/skins/1-37.json`).then((res) =>
  res.json(),
);

const finishFamily = await fetch(
  `${API_ROOT}/consumer/overlays/finish-families/case-hardened.json`,
).then((res) => res.json());

console.log(discovery.counts.skins);
console.log(discovery.overlay_counts["finish-families"]);
console.log(skin.name);
console.log(finishFamily.primary_mechanics[0].name);
console.log(skin.media.primary_image_png);
```

Resolve a stable canonical slug to an entity ID, then fetch the page-ready card:

```ts
const API_ROOT =
  "https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api";

const slugIndex = await fetch(
  `${API_ROOT}/graph/indexes/by-canonical-slug/set-gamma-2.json`,
).then((res) => res.json());

const collectionId = slugIndex.items.find((item: { kind: string; id: string }) => item.kind === "collection")?.id;

if (collectionId) {
  const collection = await fetch(`${API_ROOT}/consumer/cards/collections/${collectionId}.json`).then((res) =>
    res.json(),
  );
  console.log(collection.name);
}
```

Resolve a human-friendly search slug:

```ts
const API_ROOT =
  "https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api";

const slugIndex = await fetch(
  `${API_ROOT}/graph/indexes/by-slug/desert-eagle-blaze.json`,
).then((res) => res.json());

const skinId = slugIndex.items.find((item: { kind: string; id: string }) => item.kind === "skin")?.id;

if (skinId) {
  const skin = await fetch(`${API_ROOT}/consumer/cards/skins/${skinId}.json`).then((res) =>
    res.json(),
  );
  console.log(skin.name);
}
```

### Python

```python
import requests

API_ROOT = "https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api"

discovery = requests.get(f"{API_ROOT}/consumer/meta/discovery.json", timeout=30).json()
skin = requests.get(f"{API_ROOT}/consumer/cards/skins/1-37.json", timeout=30).json()

print(discovery["counts"]["skins"])
print(skin["name"])
print(skin["media"]["primary_image_png"])
```

Resolve a market hash name to a canonical skin variant:

```python
import requests
from urllib.parse import quote

API_ROOT = "https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api"
market_hash_name = "Desert Eagle | Blaze (Factory New)"
encoded = quote(market_hash_name, safe="")

index_payload = requests.get(
    f"{API_ROOT}/graph/indexes/by-market-hash-name/{encoded}.json",
    timeout=30,
).json()

variant_id = index_payload["items"][0]["id"]
variant = requests.get(
    f"{API_ROOT}/reference/skin-variants/{variant_id}.json",
    timeout=30,
).json()

print(variant["market_hash_name"])
print(variant["skin_id"])
```

### More Examples

Get a page-ready agent card:

```text
https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/consumer/cards/agents/5505.json
```

Get a page-ready collection card:

```text
https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/consumer/cards/collections/set_anubis.json
```

Resolve a market hash name to a skin variant:

```text
https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/graph/indexes/by-market-hash-name/Desert%20Eagle%20%7C%20Blaze%20%28Factory%20New%29.json
```

Then load the referenced variant:

```text
https://raw.githubusercontent.com/steamdashboard/cs2-items-api/main/data/api/reference/skin-variants/1-37__normal__factory-new.json
```

### Common Access Patterns

- Start with `consumer/meta/discovery.json` to learn the main entrypoints and current counts.
- Use `consumer/cards/*` when you want page-ready objects for apps, sites, or bots.
- Use `reference/*` when you want canonical normalized entities and stable IDs.
- Use `graph/indexes/*` to resolve by slug, rarity, weapon, collection, tournament, and other lookup dimensions.
- Use `media/rendered/files/*` when you need a direct PNG URL for display.
