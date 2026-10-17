# `data/` — datasets

Datasets used for demos and evaluation. One folder per dataset, versions never overwritten.

## Layout

```
data/<dataset-name>/
  card.md        # data card: source, license, fields, rows, updated, owner
  schema.json    # field definitions checked by CI
  v1/            # files for version 1
  v2/            # new version — never edit v1 in place
```

## `card.md` must answer

- **Source** — where the data came from (public page, internal tool, generated)
- **License / permission** — can it be committed here at all
- **Owner** — who to ask when it looks wrong
- **Fields** — one line per column, plus units
- **Known issues** — missing values, odd samples, trimming applied

## `schema.json`

```json
{
  "name": "example-dataset",
  "version": 1,
  "fields": [
    { "name": "id", "type": "string", "required": true },
    { "name": "score", "type": "number", "required": false, "description": "0–100" }
  ]
}
```

CI fails when `schema.json` is missing, unparseable, or has a field without `name`/`type`.

## Rules

- **No customer data.** Anonymize before it ever reaches this repo; if it cannot be anonymized, it does not belong here.
- Keep single files under 5 MB. Larger files go to Releases, small samples stay here.
- Bump the version folder instead of rewriting history.
