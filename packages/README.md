# `packages/` — internal packages

Buildable units the team distributes: SDK wrappers, tool adapters, shared configs, CLI helpers.

## Layout

```
packages/<package-name>/
  README.md        # what it does, how to install/build
  package.json     # or pyproject.toml / go.mod — one manifest per package
  src/
  test/
```

## Naming

`<package-name>` is lowercase and hyphenated; it must match the manifest name. Prefer shipping under a scope (`@kip/…`) when it is published.

## Build and release

- Every package must build from a clean checkout with one documented command.
- Binaries and archives are **never** committed. Tag a release and let the workflow attach the artifact:

  ```
  git tag <package-name>-v1.2.3
  git push mine <package-name>-v1.2.3
  ```

- Each release notes what changed and which commit it came from.

## Rules

- No secrets, no customer identifiers, no internal endpoints in package configs.
- A package without a README and a build command is treated as a draft — keep it out of `main` until both exist.
