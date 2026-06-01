---
description: Bootstrap this pms-ai install's organization + projects (renders ~/.pms-ai/{key}/config.yaml). Named /onboard to avoid Claude Code's built-in /init.
---

# /onboard — bootstrap this install's organization

Create the machine-local org config at `~/.pms-ai/{key}/config.yaml` by driving
the `pms-ai` CLI, which wraps `pms_ai.config` (the single source of truth). **Do
not write the YAML yourself.**

## Steps

1. Gather, asking the user for anything not already provided:
   - **Organization key** — short, alphabetic, spaceless (e.g. `acme`); becomes
     the `~/.pms-ai/{key}/` directory name.
   - **Organization name** — full, human-readable (e.g. `Acme Corporation`).
   - **One or more projects** — for each, a `name` (kebab/snake slug) and a
     `repo` path (prefer `~`- or `${VAR}`-relative paths for portability). The
     first project becomes the active `current_project`.
2. Run the CLI non-interactively with the collected values:

   ```bash
   pms-ai onboard --non-interactive \
     --key <key> --name "<name>" \
     --project <name1>=<repo1> [--project <name2>=<repo2> ...]
   ```

   (Or run `pms-ai onboard` with no flags to let the CLI prompt directly.)
3. Confirm success by reporting the written path and running `pms-ai show`.

## Notes

- The CLI **refuses to overwrite** an existing config — if onboarding was
  already done, point the user at `pms-ai use <project>` or editing the file.
- It validates the key (letters only, no spaces) and rejects bad input with a
  clear message — relay that to the user rather than retrying blindly.
- The generated config is **git-ignored and machine-local**; never commit it.
- To add more projects later, use the `config` skill (edit the `projects:` map,
  then `pms-ai use`).
