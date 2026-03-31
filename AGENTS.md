# Agent Instructions

This repository is a committed, file-based CS2 data API generated from local game files.

## Source Of Truth

- Treat `src/cs2_skins_api/` as the implementation source of truth.
- Treat `data/` as generated output.
- Treat `README.md`, `docs/`, tests, workflow files, and licensing files as hand-maintained project metadata.

## Editing Rules

- Do not hand-edit generated JSON under `data/` unless the user explicitly asks for a one-off manual patch.
- If a schema, normalization rule, or output contract changes, prefer updating the builder in `src/cs2_skins_api/` and regenerating output.
- Keep generated data, tests, and documentation aligned when behavior changes.
- Do not commit local-only directories such as `.cache/`, `.python_packages/`, `exports/`, or `__pycache__/`.

## Validation

Use the existing Make targets:

- `make install`
- `make check-update`
- `make update`
- `make validate`

`make validate` is the cheapest default verification step for documentation-only or contract-level changes.

## Repository-Specific Constraints

- Public metadata must not expose local filesystem paths.
- Stable IDs and file layout under `data/api/` are part of the public contract.
- Raw GitHub consumption examples in `README.md` assume a public repository.
- When changing API paths or shapes, update `README.md`, `data/api/meta/schema.json` generation, and tests together.

## Practical Guidance

- For API-facing work, inspect `data/api/meta/schema.json` and `data/api/consumer/meta/discovery.json` first.
- For agent-related entity logic, prefer the normalized reference layer first, then the consumer layer.
- Keep documentation examples pointed at real files that exist in the current generated dataset.
