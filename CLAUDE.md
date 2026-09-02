# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Personal dotfiles managed with [chezmoi](https://www.chezmoi.io). Chezmoi turns `dot_*` files in this
source repo into dotfiles in `$HOME` (`dot_bashrc` → `~/.bashrc`, etc.) and runs `run_*` scripts as part
of `chezmoi apply`.

## Commands

```sh
chezmoi apply             # apply repo state to $HOME, rerun any changed run_onchange_ scripts
chezmoi diff               # preview pending changes before applying
chezmoi re-add              # pull current $HOME state back into the repo (no push)
chezmoi cd                  # shell into the source dir (this repo, as chezmoi sees it)
chezmoi execute-template < file  # render a .tmpl file's Go-template output for debugging
```

There is no build/lint/test suite — this is dotfiles, verify by running `chezmoi apply` (or `chezmoi diff`
first) and checking the rendered output / resulting shell behavior directly.

## Structure

- `dot_bashrc`, `dot_zshrc` — shell-specific rc files (bash / oh-my-zsh). Both source `dot_shell_shared`
  at the end, which holds logic common to both shells (PATH, aliases, uv/nvm env).
- `.chezmoidata/*.yaml` — plain data (package lists, update schedule) consumed by templates via
  chezmoi's `.` context. Editing these files is the intended way to change behavior — they re-trigger
  the corresponding `run_onchange_` script on next `chezmoi apply` because chezmoi hashes the rendered
  script content (which includes the data).
- `run_onchange_after_install-packages.sh.tmpl` — installs packages listed in
  `.chezmoidata/packages.yaml` (apt, snap, uv tool). Sections are independent: one failing package
  doesn't stop the rest; failures are collected and reported at the end, script exits non-zero if any
  occurred.
- `run_onchange_after_install-zsh.sh.tmpl` — installs oh-my-zsh (`--unattended --keep-zshrc`, so it
  never touches chezmoi's `~/.zshrc`) and `chsh`es the login shell to zsh. Linux-only; no-ops when zsh
  isn't installed or when both are already set up. Chezmoi runs `after_` scripts in name order, so this
  lands after `install-packages`, which is what installs the zsh apt package it depends on.
- `run_onchange_after_install-auto-update.sh.tmpl` — installs `/usr/local/sbin/system-update` (apt
  update/upgrade + snap refresh + autoremove) plus a systemd service/timer that runs it on the schedule
  in `.chezmoidata/auto_update.yaml`. Linux-only (no-ops elsewhere); the `update` alias in
  `dot_shell_shared` runs the same installed script by hand, so the manual and scheduled paths can't
  drift apart — always edit the script inside this `.tmpl`, never `/usr/local/sbin/system-update`
  directly, since that copy is overwritten on every `chezmoi apply`.
- `dot_claude/executable_statusline-command.sh` — installs `~/.claude/statusline-command.sh`, source of
  truth for the Claude Code statusline shown in this repo's own sessions.
- `run_onchange_after_install-claude-statusline.sh.tmpl` — points `~/.claude/settings.json`'s
  `statusLine` at the installed script above. No-ops on machines without the `claude` CLI or `python3`.
  Reruns on statusline-script edits too: its own hash embeds a `sha256sum` of that script via chezmoi's
  `include` template func, so the two can't drift apart the same way the update script above doesn't.
- `.chezmoiignore` — keeps repo-only docs (this file, `README.md`) from being applied into `$HOME`;
  everything else at the repo root without a `dot_`/`run_` prefix would otherwise land there verbatim.

## Conventions specific to this repo

- To add a package: add it under the right key in `.chezmoidata/packages.yaml`, then `chezmoi apply`.
- To change the update schedule: edit `.chezmoidata/auto_update.yaml` (hours are 24h machine-local),
  then `chezmoi apply`.
- `run_onchange_` scripts are re-executed whenever chezmoi detects their *rendered* content changed, so
  editing the `.chezmoidata` YAML they depend on is enough to trigger a rerun — no need to touch the
  script file itself.
- Scripts use `set -uo pipefail` (not `-e`) plus manual `FAILURES` array collection deliberately, so one
  failed package/unit doesn't abort the rest of the script.
