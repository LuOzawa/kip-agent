# `skills/` — agent skills

One folder per skill. Every skill needs a machine-readable `skill.json` and a human-readable `SKILL.md`.

## Layout

```
skills/<skill-name>/
  skill.json     # manifest — checked by CI
  SKILL.md       # when to use it, inputs, outputs, limits
  ...            # implementation (scripts, prompts, assets)
```

## Reference example

`skills/csv-to-excel/` is a complete, runnable skill — copy its layout for new ones: `skill.json`, `SKILL.md`, `run.ts`, `samples/`. It is TypeScript with **zero npm dependencies** on purpose; that is the default we want, because a skill that needs `npm install` cannot be trusted inside a sandbox. CI runs it on every pull request, so it also serves as the smoke test for the conventions below.

## `skill.json`

```json
{
  "name": "excel-report",
  "version": "1.0.0",
  "description": "Turn a CSV into a formatted Excel report with a summary sheet.",
  "entry": "run.ts",
  "runtime": "node",
  "inputs": ["path/to/input.csv"],
  "outputs": ["out/report.xlsx"],
  "permissions": ["filesystem:read", "filesystem:write"]
}
```

| Field | Required | Notes |
|---|---|---|
| `name` | ✅ | must match the folder name |
| `version` | ✅ | semver `MAJOR.MINOR.PATCH` |
| `description` | ✅ | one sentence, no marketing |
| `entry` | ✅ | file that runs the skill |
| `runtime` | — | `node` / `python` / `bun` / `shell` — anything not listed here is assumed `node` |
| `inputs` / `outputs` | — | paths or types |
| `permissions` | — | anything beyond read-only must be declared |

## `SKILL.md` must answer

- **When to use** — the trigger, and the cases where it is the wrong tool
- **Inputs / outputs** — with an example
- **Failure modes** — what breaks, and what the agent should do instead
- **Verified on** — version and date you last ran it end to end

## Rules

- Breaking change → bump `MAJOR`. CI rejects a version that does not parse as semver.
- No credentials inside a skill. Secrets come from the runtime, never from this repo.
- A skill without `SKILL.md` is not accepted — the agent needs the prose to choose it.
