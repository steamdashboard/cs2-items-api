# Unknown Classes

The builder intentionally distinguishes between:

- `unknown blocks`: top-level structures present in `items_game` but not explicitly modeled
- `unknown prefabs`: item prefabs that are seen but not mapped into API-facing categories
- `unresolved sources`: item graphs that exist but cannot be linked to a reliable source resolver

This is deliberate.

When Valve adds a new class or delivery mechanism, the correct behavior is:

1. keep the raw source
2. emit a report
3. allow a maintainer to decide how the new class should be represented

The builder should not silently invent semantics for previously unseen structures.
