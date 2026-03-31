# Consumer Layer

## Status

This document records the research and design direction behind the consumer layer.

The authoritative current generated contract is the checked-in dataset, `README.md`, and `data/api/meta/schema.json`.

Some path names and object groupings below are early proposals and do not match the current emitted layout verbatim.

As of the current snapshot, the emitted consumer contract already includes first-class overlay groups for:

- `finish-families`
- `rare-patterns`
- `phases`
- `market-constraints`

Skin, skin-variant, and case cards also expose trading-oriented summaries that link back to those overlays.

## Goal

The consumer layer must let downstream teams build a polished CS2 wiki, market explorer, database site, or trading-oriented UI without first reverse-engineering the canonical model.

It should stay source-faithful, but it must not force consumers to understand Valve-internal naming or relation graphs before they can render useful pages.

## Terminology

The project is positioned as `cs2-items-api`.

The consumer layer is still part of the extraction-first contract.

It is not a manual CMS or a separate product feature layer. It is a deterministic, user-readable projection of source-backed entities, relations, and media.

That means consumer entrypoints should say `case`, `capsule`, `souvenir-package`, `sticker`, `agent`, and `weapon-skin` when those are the correct user-facing nouns, instead of flattening everything into a generic `item` or `container`.

## Research Summary

### User entrypoints

The dominant user entrypoints are not `rifles`, `smgs`, or generic `containers`.

The strongest entrypoints are:

- skins
- cases
- knives
- gloves
- stickers
- collections
- weapons
- finishes
- market / buy / sell / trade
- inventory value
- inspect
- float
- rare pattern terms such as fade percentage, blue gem, doppler phase

### Competitor patterns

Observed on `csgoskins.gg`, `wiki.cs.money`, and `lis-skins.com`:

- Skin pages are built around a page-ready summary, not around normalized raw records.
- Users are shown wear limits, exterior availability, collection/case origin, finish style, release/update context, and media immediately.
- Case pages are treated as first-class consumer objects.
- Rare item pools are explained in human terms like knives, gloves, or special items, not as abstract loot tokens.
- Expert fields are shown when relevant:
  - pattern difference
  - effect of float
  - fade percentage
  - doppler phase
  - blue gem tiers

### Trading / market relevance

For normal users:

- correct name
- image
- exteriors
- StatTrak / Souvenir availability
- collection / case source
- quick variant list

For advanced users:

- float range
- pattern-sensitive vs pattern-insensitive flag
- release/update provenance
- container rarity path
- inspect-ready references
- special item pool expansion
- marketability / tradability restrictions

For expert collectors and traders:

- finish-family overlays
- phase / fade / blue gem overlays
- exact pattern seed behavior
- release timing
- price and liquidity overlays, if external data is added later

## Design Principles

### 1. Consumer naming must follow human usage

The consumer layer should use:

- `case`
- `capsule`
- `souvenir-package`
- `weapon`
- `weapon-skin`
- `knife`
- `glove`
- `sticker`
- `patch`
- `graffiti`
- `agent`
- `charm`
- `music-kit`

It should not lead with umbrella names like `container` unless used as a fallback compatibility concept.

### 2. Consumer records must be page-ready

A consumer card should already answer:

- what is it
- what is it called
- how does it look
- which versions exist
- where does it come from
- what related entities matter
- what details matter for trading

### 3. Consumer layer must stay structurally derived

The consumer layer is not a manual CMS.

It may reshape the canonical graph aggressively, but every field must be either:

- sourced from game files
- deterministically derived from canonical data
- explicitly marked as overlay / external

### 4. Expert overlays must be first-class, not hidden hacks

Do not bury high-value trading concepts inside arbitrary extra fields.

Rare-pattern logic must live in dedicated overlay groups.

## Early Proposed Consumer API

```text
data/api/consumer/
  meta/
    schema.json
    discovery.json
    facets.json

  browse/
    home.json
    categories.json
    weapons.json
    finishes.json
    cases.json
    collections.json
    stickers.json
    agents.json
    charms.json
    music-kits.json
    tournaments.json

  cards/
    weapons/
    weapon-skins/
    skin-variants/
    knives/
    knife-variants/
    gloves/
    glove-variants/
    cases/
    capsules/
    souvenir-packages/
    collections/
    stickers/
    patches/
    graffiti/
    agents/
    charms/
    music-kits/
    tournaments/
    teams/
    players/

  lists/
    by-weapon/
    by-finish/
    by-finish-family/
    by-case/
    by-collection/
    by-rarity/
    by-exterior/
    by-quality/
    by-type/
    by-tournament/
    by-team/
    by-player/
    by-search-name/

  overlays/
    finish-families/
    rare-patterns/
    phases/
    fade-percentages/
    blue-gems/
    release-history/
    market-constraints/

  media/
    manifests/
    rendered/
```

## Primary Consumer Objects

### Weapon card

Purpose:

- top-level browse entity for a base weapon
- entrypoint for all weapon skins

Required fields:

- id
- name
- localized names
- consumer type
- weapon family
- side
- inspect / model refs
- image refs
- skin ids
- available finishes count
- featured skins

### Weapon skin card

This is the default skin page for ordinary weapons.

Required fields:

- id
- name
- localized names
- consumer type: `weapon-skin`
- weapon
- finish
- finish style
- finish catalog
- rarity
- collection
- source cases
- wear range
- available exteriors
- supports normal / StatTrak / Souvenir
- release summary
- update summary
- pattern behavior
- media summary
- variant ids
- related skins

### Knife card

This is not just a weapon card with `weapon_group=knife`.

Knives are a first-class consumer object because users browse them that way.

Required fields:

- id
- name
- knife type
- finish
- finish family
- finish style
- finish catalog
- available exteriors
- StatTrak support
- source cases
- rare pattern support
- phase / fade / blue gem overlay refs when relevant
- media summary

### Glove card

Gloves are also a first-class consumer object.

Required fields:

- id
- name
- glove type
- finish
- finish family
- finish style
- finish catalog
- available exteriors
- source cases
- rare pattern support when relevant
- media summary

### Case card

This is one of the highest-value consumer objects.

Required fields:

- id
- name
- localized names
- consumer type: `case`
- case series
- release summary
- update summary
- image refs
- contained items by rarity tier
- contained collections
- contained skin ids
- expanded rare special items
- StatTrak behavior
- related key if applicable

### Capsule card

Should cover:

- sticker capsules
- autograph capsules
- patch packs
- pin capsules

Required fields:

- id
- name
- capsule type
- tournament or event context when relevant
- contained sticker / patch ids
- image refs

### Collection card

Required fields:

- id
- name
- localized names
- map / operation / event context when derivable
- item class breakdown
- skin ids
- originating cases or souvenir packages

### Sticker / patch / graffiti card

Required fields:

- id
- name
- localized names
- item kind
- finish type
- tournament / team / player association
- release summary
- image refs

## Required Browse Entry Points

The consumer layer should expose strong ready-made browse lists:

- all skins
- all cases
- all knives
- all gloves
- all stickers
- all collections
- all agents
- all charms
- all music kits
- all tournament items

And also practical lists:

- skins by weapon
- skins by finish
- skins by finish family
- skins by rarity
- skins by exterior
- cases by contained knife family
- cases by contained glove family
- sticker capsules by tournament

## Required Facets

### Core facets

- type
- weapon
- knife type
- glove type
- finish
- finish style
- rarity
- exterior
- quality
- collection
- case
- tournament
- team
- player

### Expert facets

- pattern-sensitive
- supports-phase-overlay
- supports-fade-overlay
- supports-blue-gem-overlay
- StatTrak available
- Souvenir available
- released in CS2
- released in CS:GO

## Required Overlays

These must not pollute base cards.

### Finish families

Examples:

- fade
- doppler
- gamma-doppler
- case-hardened
- marble-fade
- lore

### Rare-pattern overlays

Examples:

- fade percentage
- doppler phases
- blue gem tiers
- notable high-value seeds

### Release overlays

Needed because consumers care about:

- what update added the item
- whether it is new
- whether it is legacy

### Market-constraint overlays

Derived from platform and item rules:

- marketable
- tradable
- trade-hold-relevant
- newly released waiting period if applicable

## Media Contract

The consumer layer should expose media in a direct, page-friendly shape.

Base media contract:

- primary image
- thumbnail image
- large image
- model refs
- inspect refs
- source manifest
- coverage status

Current implementation now guarantees:

- rendered semantic PNG previews for every skin
- shared rendered preview manifests for every skin variant
- explicit tier mapping between variant exteriors and preview buckets (`light`, `medium`, `heavy`)
- rendered primary PNG previews for weapons, containers, stickers, patches, graffiti, agents, charms, music kits, and tools

If no skin-specific media is currently derivable from game files, the contract must say so explicitly:

- `media_scope = weapon-base-fallback`
- `media_status = incomplete`

Do not silently pretend that a base weapon icon is a skin preview.

## Naming Pool

Consumer layer names should follow this mapping:

- `weapon-case` -> `case`
- `sticker-capsule` -> `capsule`
- `pin-capsule` -> `pin-capsule`
- `souvenir-package` -> `souvenir-package`
- `weapon skin` -> `weapon-skin`
- `knife skin` -> `knife`
- `glove skin` -> `glove`

Keep canonical source names in provenance fields:

- `source_container_kind`
- `source_prefab`
- `source_token`

## Current Gaps Blocking A Good Consumer Layer

### 1. Rare special pools are not expanded

Current placeholder entities like `unusual_revolving_list`, `gamma2_knives2_unusual`, `set_glove_3_unusual`, and `spectrum_unusual` are not enough for a consumer layer.

They must expand into actual knife / glove finish sets.

### 2. Knife and glove skins are missing from skin-level browse

These must become first-class consumer records.

### 3. Finish style is only stored as a code

Consumer layer needs a normalized human label, not just `style_code`.

### 4. Release/update provenance is not modeled strongly enough

Consumer pages need:

- first seen build
- release date
- update name

### 5. Media honesty must be preserved

If a skin uses fallback media, that must be explicit in the contract.

## Acceptance Criteria

The consumer layer is good when:

- a wiki can render a full skin page from one consumer card plus linked overlays
- a market explorer can build filter pages without decoding raw reference entities
- a collector can answer float / pattern / origin questions cleanly
- a normal user can browse cases, knives, gloves, and skins using familiar names
- no consumer object depends on Valve-internal wording for discoverability
