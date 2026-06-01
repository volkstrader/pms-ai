---
title: pms-ai — subsystem roadmap
status: Living roadmap
created: 2026-05-31
reference: a prior internal reference implementation ("agenthq"), kept private — local path in project memory
---

# pms-ai — Subsystem Roadmap

High-level map of the work, so deferred subsystems aren't lost while we build the foundation.
Each subsystem below (except #1) is **roadmap-level only** — it still needs its own
brainstorm → spec → plan → implementation cycle before any code. This file records *enough to come
back later*: goal, scope boundary, dependencies, and the open questions to resolve on return.

## North Star

**`pms-ai` is a staging ground for projects; dynamic multi-agent workflows are the execution
engine.** You stage a project (identity, config, requirements, plan, artifacts) inside pms-ai;
a dynamically-composed workflow reads that staged state and drives the work to completion. pms-ai
is the durable control plane; workflows are ephemeral execution. Distributed as a clean Claude Code
marketplace plugin + vendored Python CLI; a clean-room generalization of the `agenthq` reference.

## Build Order & Dependencies

```
#1 Plugin + Config Core  ──►  #2 Staged-Project / Artifact Model  ──►  #3 Dynamic Workflow Engine
   (staging-ground                 (what is "ready to execute")            (run the staged project)
    foundation)                              │                                      │
                                             └──────────────►  #4 Visualization  ◄──┘
                                                            (Astro 6 + Bun → Cloudflare)
```

- **#1 before all** — nothing can be staged until the org home, identity, and config exist.
- **#2 before #3** — a workflow needs a defined, machine-readable "staged project" to consume.
- **#4 after #2** (can read static project state), richer once **#3** emits workflow/run state.

| # | Subsystem | Status | Depends on | Rough size |
|---|-----------|--------|------------|-----------|
| 1 | Plugin + Config Core | Spec drafted (`2026-05-31-pms-ai-plugin-config-core-design.md`) | — | M |
| 2 | Staged-Project / Artifact Model | Roadmap only | #1 | M |
| 3 | Dynamic Workflow Execution Engine | Roadmap only | #2 | L |
| 4 | Visualization (Astro/Cloudflare) | Roadmap only | #2 (min), #3 (full) | M |

---

## #2 — Staged-Project / Artifact Model

**Goal.** Define what artifacts make up a "staged project" and when it is *ready to execute* — the
contract the workflow engine (#3) consumes and the visualization (#4) renders.

**Scope (to be designed).**
- The artifact set per project (e.g. requirements/PRD, plan, task graph, decisions) and where it
  lives in the external project repo (`projects: {name: {repo}}` from #1).
- A machine-readable manifest describing the project's executable state (tasks, dependencies,
  status, gates) — the "is this ready to run?" definition.
- Read/write helpers in `pms_ai` (artifacts are data the plugin reads; staying consistent with
  `pms_ai.config` as the only schema owner pattern).
- Folder-as-entity conventions (kebab-case slugs, archive mirrors) generalized from agenthq.

**Depends on.** #1 (org/project config + repo path resolution).

**Open questions for the return brainstorm.**
- What exactly is the unit of work the workflow executes — a task, a phase, a whole project?
- Artifact format: markdown + YAML frontmatter (agenthq style) vs a structured manifest file?
- How much of agenthq's plan→PRD→TDD pipeline generalizes vs is specific to that prior tool?
- Where does GitHub fit (issues/Projects as a data plane), if at all, given the workflow-first
  execution model replaces agenthq's GitHub-orders approach?

**Patterns to reuse (agenthq ref).** plan/PRD/roadmap templates, folder-as-entity config,
strategic vs operational stage taxonomies, structured-JSON contracts.

---

## #3 — Dynamic Workflow Execution Engine

**Goal.** Turn a staged project (#2) into a **dynamically-composed** multi-agent workflow and run it
to completion — fan-out/pipeline shaped by the staged task graph, not a fixed script.

**Scope (to be designed).**
- How a staged project is read and compiled into a workflow shape (parallel vs pipeline vs
  loop-until-done) from its task graph/dependencies.
- The execution substrate (Claude Code's Workflow primitive / multi-agent orchestration) and how
  pms-ai invokes it — ephemeral runs, no long-lived field agents.
- Run state: where progress, results, and verification verdicts are written back (into the project
  artifacts of #2, for #4 to render).
- Gates / human-in-the-loop checkpoints; adversarial verification of outputs.

**Depends on.** #2 (the executable definition) and #1 (config/secrets/env).

**Open questions for the return brainstorm.**
- "Dynamic" mechanism: does pms-ai generate a workflow script per project, or drive a generic
  workflow engine parameterized by the task graph?
- Idempotency/resumability of runs; partial completion and re-staging.
- Verification strategy (which quality patterns: adversarial verify, completeness critic, etc.).
- Concurrency, budget, and isolation (worktrees) when work mutates project repos in parallel.

**Patterns to reuse (agenthq ref).** dispatch/fan-out semantics, review-tdds-style cross-checks,
structured-JSON agent contracts. (Replace standing field Librarians with ephemeral workflow agents.)

---

## #4 — Visualization (Astro 6 + Bun → Cloudflare)

**Goal.** A site that visualizes staged projects and workflow runs — the human-facing window into
pms-ai's control plane and execution state.

**Scope (to be designed).**
- Astro 6 app, Bun as runtime/package manager, deployed to **Cloudflare** (Pages/Workers; Astro
  Cloudflare adapter).
- Data source: reads the staged-project artifacts (#2) and workflow run state (#3). Decide
  static-build vs SSR/edge vs a small API.
- Where it lives: its own external repo (registered as a project) vs a `web/` area; how it's built
  and deployed (wrangler / CI).
- Views: project overview, task graph/status, run timelines, verification results.

**Depends on.** #2 (minimum — static project state); richer with #3 (live run state).

**Open questions for the return brainstorm.**
- Static vs dynamic: build-time generation from artifacts, or live edge reads of run state?
- Auth/access for the Cloudflare site (public, org-private, per-project)?
- How the build is triggered (on artifact change, on workflow completion, manual deploy)?
- Does the viz live in pms-ai or in a separate repo the plugin scaffolds?

**Patterns to reuse (agenthq ref).** agenthq used GitHub Project boards as its operational UI and
planned a `web/` (Astro + React islands) repo — this subsystem supersedes that with a first-class
Astro 6 + Bun + Cloudflare layer.

---

## How to resume any subsystem

1. Read this roadmap entry + the North Star.
2. Run the `brainstorming` skill on that subsystem's open questions.
3. Write its spec to `docs/superpowers/specs/YYYY-MM-DD-pms-ai-<subsystem>-design.md`.
4. Use `writing-plans` to produce the implementation plan; execute (a dynamic workflow is a natural
   fit once #3 exists).
