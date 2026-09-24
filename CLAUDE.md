# CLAUDE.md

## What this repo is

Personal dotfiles managed with [chezmoi](https://www.chezmoi.io): `dot_*` files here become dotfiles in
`$HOME` (`dot_bashrc` → `~/.bashrc`), and `run_*` scripts execute during `chezmoi apply`.

**This working clone is not chezmoi's source dir.** Chezmoi reads `~/.local/share/chezmoi` — what
`chezmoi cd` opens, and on this machine a *separate* clone of the same remote. Edits here change
nothing until they are pushed and pulled there, so the loop is: edit, commit and push here, then
`chezmoi update`. Run `chezmoi source-path` to check on any machine.

## Commands

```sh
chezmoi update                    # git pull in the source dir, then apply — the normal path
chezmoi apply                     # apply source-dir state to $HOME, rerun changed run_onchange_ scripts
chezmoi diff                      # preview pending changes
chezmoi re-add                    # pull current $HOME state back into the source dir
chezmoi execute-template < file   # render a .tmpl for debugging
```

No build/lint/test suite: verify with `chezmoi diff`, then `chezmoi apply`, then check the resulting
shell behavior. Test risky script changes in a throwaway container or user account — the live machine
is already in the post-install state, so it only exercises the no-op path.

## Structure

- `dot_bashrc`, `dot_zshrc` — bash / oh-my-zsh rc files. Both source `dot_shell_shared` at the end
  (PATH, aliases, uv/nvm env). nvm is lazy-loaded: sourcing `nvm.sh` cost ~0.15s of every new shell,
  and its default `nvm use` (which spawns npm/node) ~0.5s more. Instead the default alias's newest
  matching version goes on PATH by hand (with `NVM_BIN`/`NVM_INC`, as `nvm use` sets them), and `nvm`
  is a stub that sources the real one plus its completion on first call — so `nvm` tab completion
  only works after the first `nvm` command in a shell. A version already on PATH (inherited from a
  parent shell) is kept, as nvm does. Aliases that aren't a version prefix (`lts/*`, `node`) fall back
  to a real `nvm use`.
- `dot_zshenv` — sets `skip_global_compinit=1`, so Ubuntu's `/etc/zsh/zshrc` doesn't run a compinit
  that oh-my-zsh repeats anyway. Ends by sourcing `~/.custom_zshenv`: installers such as rustup append
  to `~/.zshenv`, which chezmoi would overwrite, so those lines belong there instead.
- `dot_zprofile` — sources `~/.profile` (in sh emulation) for zsh login shells, which don't read it
  themselves. The GNOME session starts via `$SHELL -l`, so without it desktop-launched apps lose the
  PATH `~/.profile` builds once `install-zsh` makes zsh the login shell. `~/.profile` stays unmanaged:
  it's the distro default plus machine-local entries.
- Machine-local hooks: `~/.custom_shell_shared` (end of `dot_shell_shared`), then `~/.custom_bashrc` /
  `~/.custom_zshrc` (end of the rc files), plus `~/.custom_zshenv` (end of `dot_zshenv`, for every zsh,
  scripts included), each sourced only if present. They are deliberately absent
  from this repo, so chezmoi never writes them — per-machine settings go there, not in the managed files.
  `dot_bashrc` sets its `HISTSIZE`/`HISTFILESIZE` defaults *after* `~/.custom_bashrc`, only if unset:
  assigning `HISTFILESIZE` truncates the history file immediately, so an earlier default would cut
  history before a larger custom value took effect.
- `.chezmoidata/*.yaml` — data (package lists, update schedule) read by templates through chezmoi's `.`
  context. Editing these is the intended way to change behavior: it changes the rendered script
  content, which is what makes the matching `run_onchange_` script rerun.
- `run_onchange_after_install-packages.sh.tmpl` — installs `.chezmoidata/packages.yaml` (apt, snap, uv
  tool). Sections are independent; failures are collected, reported at the end, and exit non-zero.
  Packages a machine can't provide — apt packages missing from its release's repos (checked with
  `apt-cache show`), or the whole snap section when `snap` isn't installed — are skipped with a
  warning instead, so they don't block the `after_` scripts that sort later.
- `run_onchange_after_install-zsh.sh.tmpl` — installs oh-my-zsh (`--unattended --keep-zshrc`, so it
  never replaces chezmoi's `~/.zshrc`) and `chsh`es the login shell to zsh through sudo, adding zsh to
  `/etc/shells` first if needed. Linux-only; no-ops when zsh is absent or both steps are already done.
  Its name sorts after `install-packages` — chezmoi runs `after_` scripts in name order — which is what
  installs the zsh apt package it depends on.
- `run_onchange_after_install-auto-update.sh.tmpl` — installs `/usr/local/sbin/system-update` (apt
  update/upgrade, snap refresh, autoremove) plus a systemd service/timer on the schedule in
  `.chezmoidata/auto_update.yaml`. Linux-only. Always edit the script *inside* this `.tmpl`, never
  `/usr/local/sbin/system-update` — that copy is overwritten every apply, and `dot_shell_shared`'s
  `update` alias runs it, so manual and scheduled paths can't drift apart. Upgrades use
  `--with-new-pkgs` (as unattended-upgrades does) so updates needing a new dependency aren't held back.
  This complements unattended-upgrades rather than duplicating it: u-u is limited to the security
  origins, so third-party repos and `-updates` only get applied here.
- `dot_claude/executable_statusline.py` — source of truth for `~/.claude/statusline.py`: a stdlib-only
  uv script (PEP 723 header) printing a titled 2-row table with aligned columns: model | context
  bar | folder, then effort | session bar | git branch + status.
- `run_onchange_after_install-claude-statusline.sh.tmpl` — points `~/.claude/settings.json`'s
  `statusLine` at `uv run --quiet --script ~/.claude/statusline.py`. No-ops without the `claude` CLI
  or `python3`; doesn't need `uv` yet, since it runs before install-packages. Its own hash embeds a
  `sha256sum` of the statusline script (chezmoi's `include` func), so editing that script reruns this.
- `.chezmoiignore` — keeps repo-only docs (this file, `README.md`) out of `$HOME`; root files without a
  `dot_`/`run_` prefix would otherwise land there verbatim.

## Conventions

- Add a package: put it under the right key in `.chezmoidata/packages.yaml`, then apply.
- Change the update schedule: edit `.chezmoidata/auto_update.yaml` (hours are 24h machine-local), apply.
- Scripts use `set -uo pipefail` (not `-e`) plus a manual `FAILURES` array on purpose, so one failed
  package or unit doesn't abort the rest.
