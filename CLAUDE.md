# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

This repository is a freshly-initialized scaffold. As of this writing it contains only
`README.md`, `LICENSE`, and a `.gitignore` (GitHub's standard Python template) — there is no
source code, dependency manifest, build system, or test suite yet.

**There is nothing to build, lint, or test today.** The sections below should be filled in as
the project takes shape; until then, do not assume any tooling exists.

## Architecture intent

This repo holds **only AI primitives and scripting logic** — it is the public, open-source code.
The **actual data lives in a separate directory (likely its own git repo)** and is deliberately
*not* part of this repository. When writing code, treat the data location as an external,
configurable input (e.g. a path from an env var / config), never hard-code it or vendor data into
this tree.

## Security — public open-source repo

This repository is **public**. Nothing secret may ever be committed.

- **Never commit** API keys, tokens, credentials, private keys, or any sensitive data — not in
  source, tests, fixtures, notebooks, commit messages, or example files.
- Load secrets from the environment or local untracked config (`.env`, etc., which are
  gitignored). Commit only a non-secret `.env.example` documenting required variable *names*.
- Keep all real data in the separate data directory; do not copy datasets that may contain
  sensitive information into this repo.
- Before committing, double-check diffs for accidentally embedded secrets or data.

## Project

- **Name:** pms-ai — "Project Management System AI"
- **Language:** Python (inferred from the `.gitignore`; the framework/runtime is not yet chosen).
  The framework names appearing in `.gitignore` (Django, Flask, Scrapy, Celery, poetry, pdm, etc.)
  are template boilerplate, **not** committed choices.
- **Remote:** `git@github.com:volkstrader/pms-ai.git` (default branch `main`)

## To fill in as the codebase grows

When real code is added, update this file with:

- **Commands** — how to install dependencies, run the app, run the full test suite, run a single
  test, and lint/format. Document the actual tool chosen (e.g. poetry/pdm/pip, pytest, ruff).
- **Architecture** — the big-picture structure that spans multiple files and isn't obvious from a
  directory listing: entry points, module boundaries, data models, and how requests/jobs flow
  through the system.
