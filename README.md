# KIP Agent — team workspace

Shared repository for the KIP Agent team: a place to push branches, datasets, skills and packages.

| Path | What goes here |
|---|---|
| [`data/`](data/README.md) | datasets and samples — card + schema required |
| [`skills/`](skills/README.md) | agent skills — `skill.json` + `SKILL.md` |
| [`packages/`](packages/README.md) | internal packages — buildable, released by tag |
| `docs/` | design notes, specs and release checklists |

## Working here

- `main` stays clean and reviewable; do your work on `feat/…`, `fix/…`, `docs/…` branches and open a pull request.
- Commits follow conventional prefixes (`feat:`, `fix:`, `docs:`, `chore:`).
- Large binaries go to Releases, not to git history.

## Rules

- No API keys, credentials or customer data — ever.
- No real customer files in `data/`; anonymize before pushing.
- Anything security-sensitive is configured through the product, not committed here.

## Visibility

Public: anyone may read, fork and open pull requests. The team reviews and merges.

---

Contact: LuOzawa — lin700573@gmail.com
