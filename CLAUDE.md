# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What pms-ai is

**`pms-ai` is a staging ground for projects; dynamic multi-agent workflows are the execution
engine.** You stage a project (identity, config, requirements, plan, artifacts) inside pms-ai, then
a dynamically-composed workflow reads that staged state and drives the work to completion. pms-ai
is the durable control plane; workflows are ephemeral execution.

It is distributed as a **clean public Claude Code marketplace plugin** with a **vendored Python
CLI** (`pms-ai`). It is a clean-room generalization of a prior internal reference implementation
(codename "agenthq") — patterns borrowed, no product-specific details.

## Current state (2026-05-31): design phase

No application code exists yet. The design is captured in committed specs — **read these first**:

- `docs/superpowers/specs/2026-05-31-pms-ai-plugin-config-core-design.md` — **Approved** spec for
  subsystem #1 (plugin + config core / staging-ground foundation). This is what gets built next.
- `docs/superpowers/specs/2026-05-31-pms-ai-roadmap.md` — the four-subsystem map, build order, and
  the open questions for subsystems #2–#4.

There are no build/lint/test commands yet; add them here once `pyproject.toml` and `src/pms_ai/`
land.

## Architecture (summary — see spec #1 for detail)

- **Distribution:** clean marketplace plugin (repo is also its own marketplace via
  `.claude-plugin/marketplace.json`). **No fork** — per-org variation is config + data the plugin
  reads; update via `/plugin update`.
- **Hybrid substrate:** plugin layer (skills/commands) + **vendored** Python under `src/pms_ai/`.
  `pms_ai.config` is the **single source of truth** for config logic; the `config` skill and the
  `pms-ai` CLI both wrap it (never reimplement it).
- **Config — one install = one org:** `~/.pms-ai/{key}/config.yaml` (dir = `organization.key`,
  a short/alphabetic/spaceless id) holds `organization:{key,name}`, `current_project`, and
  `projects:{name:{repo}}`. The template ships inside the `config` skill; **`/onboard`** (slash
  command; CLI pairing `pms-ai onboard`; named to avoid Claude Code's built-in `/init`) renders the
  local, gitignored instance. `pms-ai use <project>` rewrites `current_project`. `PMS_AI_HOME`
  overrides the `~/.pms-ai` root for tests.
- **Secrets:** env-only/decoupled — code reads `os.environ`; run under `varlock run --` or
  `infisical run --`; commit `.env.schema` + `.env.example`; never commit resolved secrets.
- **Data:** PMS artifacts live in **external project repos** referenced by path; never vendored.
- **Visualization (subsystem #4, later):** Astro 6 + Bun, deployed to a **Cloudflare** site.

## Next step

Subsystem #1's spec is approved. The next action is to turn it into an implementation plan
(invoke the `writing-plans` skill against the approved spec), then implement: plugin manifest +
marketplace, `pms_ai.config` module with tests, the `config` skill + `/onboard` command, the
`pms-ai` CLI (`onboard`/`use`/`show`), `.env.schema` + `.env.example`, and `pyproject.toml`.
Per the project vision, executing that plan via a dynamic workflow is a natural fit.

## Security — public open-source repo

This repository is **public**. Nothing secret may ever be committed.

- **Never commit** API keys, tokens, credentials, private keys, or sensitive data — in source,
  tests, fixtures, config, or commit messages. Secrets come from the environment only.
- Keep real data in the external project repos; do not copy datasets into this repo.
- Do not commit local/identifying details (absolute home paths, private project/product names) into
  the public tree — genericize them in committed docs.
- `.gitignore` is hardened against `.env*`, `*.pem`/`*.key`/`*.p12`/`*.pfx`, `credentials.json`,
  `service-account*.json`, `secrets.*`, `*.local.json`, and `.obsidian/`. Re-check diffs before
  committing.
