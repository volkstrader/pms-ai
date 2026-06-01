---
name: config
description: Manage this pms-ai install's organization + project configuration (~/.pms-ai/{key}/config.yaml). Use when the user wants to onboard an org, add or switch projects, inspect the active project, or understand pms-ai config. Wraps the pms-ai CLI / pms_ai.config — never parse the YAML by hand.
---

# pms-ai configuration

`pms_ai.config` is the **single source of truth** for config logic. This skill,
the `/onboard` command, and the `pms-ai` CLI all wrap it. **Never read or write
`config.yaml` yourself** — always go through the CLI (or import `pms_ai.config`),
so the skill and the CLI can't drift into two incompatible readers.

## Model — one install = one org

A single install represents exactly one organization. Config lives at
`~/.pms-ai/{key}/config.yaml`, where `{key}` is `organization.key` (a short,
alphabetic, spaceless id that doubles as the directory name). `PMS_AI_HOME`
overrides the `~/.pms-ai` root.

```yaml
organization:
  key: acme                     # short, alphabetic, spaceless
  name: Acme Corporation        # free-form display name
current_project: web            # active context; `pms-ai use <name>` rewrites this
projects:
  web:   { repo: ~/repos/acme-web }
  infra: { repo: ~/repos/acme-infra }
```

The generated config is **machine-local and git-ignored** (it holds absolute
paths + mutable state). The only committed artifact is the template at
`skills/config/config.template.yaml`, which `/onboard` renders from.

## Operations (always via the CLI)

- **Onboard / bootstrap** — `pms-ai onboard` (or the `/onboard` command). Prompts
  for org key + name + one-or-more projects; writes the local config.
  Non-interactive: `pms-ai onboard --non-interactive --key acme --name "Acme Corporation" --project web=~/repos/acme-web`.
- **Switch active project** — `pms-ai use <name>` (rewrites only `current_project`).
- **Inspect** — `pms-ai show` prints the org, projects, the resolved active
  project, and required-secret status (read from the environment only).

## Adding more projects after onboarding

There is no `add` subcommand yet. To register another project, edit the
`projects:` map in `~/.pms-ai/{key}/config.yaml` — add a
`name: { repo: ~/path/to/repo }` line (prefer `~`- or `${VAR}`-relative paths) —
then `pms-ai use <name>` to make it active. Confirm with `pms-ai show`.

## Active-project resolution order

`--project` flag → `PMS_AI_PROJECT` env → `current_project` in config → the sole
project if exactly one exists → otherwise an error asking you to pick one.

## Secrets

Code reads `os.environ` only; it never stores secrets. Inject at runtime with
`varlock run -- pms-ai ...` or `infisical run -- pms-ai ...`. The repo commits
`.env.schema` (names only) and `.env.example`; never commit resolved secrets or
the generated `config.yaml`.
