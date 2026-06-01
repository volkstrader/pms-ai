---
title: pms-ai — plugin + config core (staging-ground foundation)
status: Approved (2026-05-31)
created: 2026-05-31
subsystem: 1 of 4
reference: a prior internal reference implementation ("agenthq"), kept private — local path in project memory, not a dependency
---

# pms-ai — Plugin + Config Core (Staging-Ground Foundation)

## Context & Vision

**`pms-ai` is a staging ground for projects; dynamic multi-agent workflows are the execution
engine.** You stage a project inside pms-ai — its identity, configuration, requirements, plan, and
artifacts — and then a dynamically-composed workflow reads that staged definition and drives the
work to completion. pms-ai itself is the durable, inspectable "control plane"; the workflows are
ephemeral execution spun up from staged state.

`pms-ai` is distributed as a **clean public Claude Code marketplace plugin** with a **vendored
Python CLI**. It is a **clean-room generalization** of a half-baked prior internal reference
implementation (codename "agenthq"), which we treat as a *reference example only* — we borrow its
proven patterns (command→skill→agent decomposition, folder-as-entity config, the
`docs/superpowers/specs/` convention) but copy none of its product-specific (Firebase / tax-domain)
details. In the new model, that prior tool would simply be *one org's config + data* (e.g.
`~/.pms-ai/acme/`), never plugin code.

This spec covers **subsystem #1 only: the plugin shell + the configuration core** that everything
else stands on. A workflow cannot read a staged project until the project's home, identity, and
config exist — so this is unambiguously the foundation, built first.

## Scope

**In scope (this spec):**
- Marketplace-plugin packaging and clean install/update model (no fork).
- Hybrid substrate: Claude Code plugin layer + vendored Python CLI, with a single source of truth
  for config logic.
- The `~/.pms-ai/{org}/config.yaml` model (one install = one org) and its full lifecycle.
- The `config` skill, the `/onboard` command, and the `pms-ai` CLI surface for config.
- Env-only secrets handling (varlock / infisical) and repo hygiene.

**Out of scope (each gets its own later spec):**
- **#2 Staged-project / artifact model** — what artifacts define a project that is *ready to
  execute* (requirements, plan, task graph), generalized from agenthq's plan/PRD/TDD pipeline.
- **#3 Dynamic workflow execution engine** — how a staged project is turned into a dynamically
  composed multi-agent workflow and run to completion.
- **#4 Visualization** — Astro 6 + Bun building a site (deployed to Cloudflare Pages/Workers) over
  project and workflow state.

## Architecture Overview

```
┌─────────────────────────── pms-ai (marketplace plugin) ───────────────────────────┐
│  Plugin layer (Claude Code)            Vendored Python (src/pms_ai/)                │
│    commands/  skills/  agents/   <───►   pms_ai.config  (single source of truth)    │
│    (config skill, /onboard, ...)         pms_ai.cli                                 │
└────────────────────────────────────────────────────────────────────────────────────┘
        │ reads/writes                                  │ reads
        ▼                                               ▼
  ~/.pms-ai/{key}/config.yaml  (staging-ground state)   environment (secrets via varlock/infisical)
        │ references
        ▼
  external project repos  (the staged artifacts / data; subsystem #2)
        │ consumed by
        ▼
  dynamic workflows (subsystem #3)  ──►  visualization site (subsystem #4)
```

## Distribution — clean marketplace plugin

- `pms-ai` is a public Claude Code plugin published through a marketplace. The repo is **both** the
  plugin and its own marketplace (`.claude-plugin/marketplace.json` pointing at `.`).
- Install: `/plugin marketplace add <git-url>` → `/plugin install pms-ai@<marketplace>`. The
  installed copy lives in Claude's managed plugin cache.
- **No fork.** Updates come via `/plugin update`. Per-org variation is expressed entirely through
  config + data the plugin *reads*, never by editing plugin code.

## Repo Layout

```
pms-ai/                                  (public; this repo)
  .claude-plugin/plugin.json
  .claude-plugin/marketplace.json        # self-hosting marketplace
  commands/
    onboard.md                           # /onboard -> generates ~/.pms-ai/{key}/config.yaml
                                         #   (named to avoid colliding with Claude Code's /init)
  skills/
    config/
      SKILL.md                           # owns the template + config management guidance
      config.template.yaml               # committed template /onboard renders from
  agents/                                # (primitives land here in later specs)
  src/pms_ai/                            # vendored Python (bundled with the plugin)
    __init__.py
    config.py                            # SINGLE SOURCE OF TRUTH for config logic
    cli.py                               # `pms-ai` CLI entry point
  .env.schema                            # varlock schema (committed, non-secret)
  .env.example                           # documents required env var names
  pyproject.toml
  .gitignore                             # hardened (already in place)
  CLAUDE.md
  docs/superpowers/specs/...
```

## Substrate — hybrid plugin + vendored Python

The plugin layer (skills/commands) handles natural-language orchestration and human-facing flow;
the vendored Python handles deterministic operations (parse/validate/rewrite config, resolve
paths). **The one discipline that makes hybrid safe:** `pms_ai.config` is the *only* code that
knows the config schema and file locations. Both surfaces wrap it — they never reimplement it:

- `/onboard` and the `config` skill invoke `pms-ai <subcommand>` (or import `pms_ai.config`).
- The `pms-ai` CLI exposes the same operations directly.

This prevents the classic hybrid failure mode where a skill and a CLI drift into two incompatible
config readers.

## Configuration Model — one install = one org

A single plugin install represents exactly one organization. The org identity is established once,
at `/onboard` time, and there is no multi-org selection to get wrong.

**Location:** `~/.pms-ai/{key}/config.yaml`, where `{key}` is `organization.key` — a short,
spaceless, alphabetic identifier that is safe to use as the on-disk directory name. Override the
`~/.pms-ai` root via `PMS_AI_HOME` for tests/CI.

**Schema:**
```yaml
organization:
  key: acme                     # short alphabetic id, no spaces; = the ~/.pms-ai/{key}/ dir name
  name: Acme Corporation        # full human-readable name (free-form)
current_project: web            # active context; `pms-ai use <name>` rewrites this
projects:
  web:   { repo: ~/repos/acme-web }     # ~- or ${VAR}-relative paths preferred for portability
  infra: { repo: ~/repos/acme-infra }
```

`organization.key` is validated as short + alphabetic + spaceless (it doubles as the directory
name); `organization.name` is free-form display text.

**Lifecycle:**
1. **Template** (`skills/config/config.template.yaml`) is committed inside the plugin — forkless,
   versioned, the thing `/onboard` renders from.
2. **`/onboard`** prompts for the org `key` + full `name` + initial project(s)/repo paths and
   writes the local `~/.pms-ai/{key}/config.yaml`.
3. The **generated config is machine-local** (holds absolute paths + mutable `current_project`); it
   is never committed anywhere. The template is the only committed artifact.
4. **`pms-ai use <project>`** rewrites `current_project` (kubectl-style active context).

**Resolution order for the active project:** explicit `--project` flag → `PMS_AI_PROJECT` env →
`current_project` in config → error if none and more than one project exists.

## Secrets — env-only / decoupled

- Plugin/CLI code reads `os.environ` only. It never imports a secrets SDK and never stores secrets.
- Secrets are injected at runtime by the user's tool of choice: `varlock run -- pms-ai ...` or
  `infisical run -- pms-ai ...`. Both work interchangeably because the code only sees env vars.
- The repo commits a non-secret **`.env.schema`** (varlock; documents + validates required vars)
  and **`.env.example`**. No resolved secrets are ever committed.
- `.gitignore` is already hardened against `.env.*`, `*.pem`, `*.key`, `credentials.json`,
  `service-account*.json`, `*.local.json`, etc., with `!.env.example` un-ignored.

## Components (each isolated, with a clear interface)

**`pms_ai.config` (Python module) — the single source of truth.** Purpose: locate the org config,
load + validate it, resolve the active project to an absolute repo path, and rewrite
`current_project`. Interface (shape, to be finalized in the plan):
- `home() -> Path` — `$PMS_AI_HOME` or `~/.pms-ai`.
- `load() -> Config` — find the single org dir under `home()`, parse + validate `config.yaml`,
  raise a clear "run /onboard first" error if absent.
- `resolve_project(name: str | None) -> Project` — apply the resolution order above; return name +
  expanded absolute `repo` path.
- `use(name: str) -> None` — validate the project exists, rewrite `current_project` in place.
- `init(org_key: str, org_name: str, projects: dict) -> Path` — validate `org_key` (short,
  alphabetic, spaceless), render the template to a new local config at `home()/{org_key}/`.
- Depends on: a YAML parser + a typed model (pydantic recommended). Pure; no network, no secrets.

**`config` skill.** Purpose: own the template and guide configuration management. Uses the CLI /
module; does not parse YAML itself.

**`/onboard` command.** Purpose: interactive org/project bootstrap → calls `pms_ai.config.init`.
Named `/onboard` (not `/init`) to avoid colliding with Claude Code's built-in `/init`.

**`pms-ai` CLI (`pms_ai.cli`).** Purpose: thin command surface (`onboard`, `use`, `show`,
`config …`) over `pms_ai.config`; `pms-ai onboard` is the CLI pairing for the `/onboard` slash
command. Declared as a console script in `pyproject.toml`.

## Patterns borrowed from the agenthq reference (re-derived for the generic case)

- **command → skill → agent** separation of concerns (commands route, skills know how, agents
  decide).
- **Folder-as-entity** config: a directory plus a `config.yaml` describes an entity. agenthq's
  `gh_owner` + stage taxonomies become the generic `organization` + `projects` schema; we drop the
  product-specific keys.
- **`docs/superpowers/specs/YYYY-MM-DD-*-design.md`** spec convention (this file).

## Verification

End-to-end checks once implemented:
1. **Packaging:** `/plugin marketplace add <path>` + `/plugin install` succeeds; `/onboard` and
   `pms-ai` are available.
2. **Config module (unit):** with `PMS_AI_HOME` pointed at a temp dir — `init()` writes a valid
   config; `load()` round-trips it; `resolve_project()` honors flag > env > `current_project`;
   `use()` rewrites only `current_project`; `load()` on a missing config raises the
   "run /onboard first" error.
3. **`/onboard` flow:** generates `~/.pms-ai/{key}/config.yaml` from the template with the entered org
   `key`/`name` + project paths; rejects a `key` with spaces/non-alpha chars; file is git-untracked
   (not under any repo).
4. **Secrets:** `pms-ai show` reads a required key only from the environment; running bare (no
   env) fails clearly; `varlock run -- pms-ai show` / `infisical run -- pms-ai show` succeed.
5. **Hygiene:** `git check-ignore` confirms secret patterns are ignored and `.env.example` is not.

## Open Questions / Decisions Deferred

- CLI framework (typer vs click vs argparse) and YAML/validation lib (pydantic + ruamel/pyyaml) —
  decided at planning time; not architecturally significant.
- Exact `/onboard` prompt UX (single project vs multiple at bootstrap).
- Subsystems #2–#4 are intentionally unaddressed here.
