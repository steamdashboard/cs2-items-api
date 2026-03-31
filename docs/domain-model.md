# Domain Model

## Core Principles

- `weapon` is not the same thing as `paint kit`
- `paint kit` is not the same thing as `skin`
- `skin` is not the same thing as `market variant`
- `container` is not the same thing as `collection`
- expert overlays such as rare patterns, phases, and fade percentages must not distort the core graph

## Entity Layers

### Source

Directly extracted from the installed game:

- Steam app manifest
- `items_game.txt`
- `resource/csgo_*.txt`

### Core

Normalized but still game-native:

- prefabs
- item definitions
- paint kits
- sticker kits
- item sets
- loot lists
- music definitions
- keychain definitions
- locale token maps

### API

Consumer-facing derived entities:

- weapons
- skins
- skin variants
- collections
- containers
- stickers
- sticker capsules
- agents
- charms
- music kits
- tools

## Skin Semantics

In this repository:

- a `weapon` is the paintable base item definition from the game
- a `finish` is the paint kit
- a `skin` is the deterministic combination of `weapon_id + paint_kit_id`
- a `skin variant` is a skin plus quality and exterior, derived from source availability rules

## Source Graph

The builder resolves skins from multiple source shapes:

- `item_sets`: canonical grouped sets of skin entries
- `client_loot_lists`: drop graph, case graph, sticker capsule graph, music kit box graph
- container items: links to loot lists through name, tags, supply crate series, and fallback aliases

