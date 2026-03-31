# ID Policy

## Primary Rule

Whenever the game provides a stable ID, that ID is preserved as the primary identifier.

## IDs By Entity

- item definition: original `items_game.items` key
- paint kit: original `items_game.paint_kits` key
- sticker kit: original `items_game.sticker_kits` key
- keychain definition: original `items_game.keychain_definitions` key
- music definition: original `items_game.music_definitions` key
- item set: original `items_game.item_sets` key
- loot list: original `items_game.client_loot_lists` key

## Derived IDs

Derived entities use stable composed IDs built from original source IDs:

- skin: `<weapon_id>-<paint_kit_id>`
- skin variant: `<skin_id>__<quality>__<exterior>`

If an entity cannot be tied to a real game-native identifier, the builder keeps the source references in `game_ref`.

