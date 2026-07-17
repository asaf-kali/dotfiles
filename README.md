# dotfiles

Managed with [chezmoi](https://www.chezmoi.io). See docs there.

## New machine setup

One-time bootstrap. Installs chezmoi, clones this repo, applies dotfiles, runs the package installer:

```sh
sh -c "$(curl -fsLS https://chezmoi.io/get)" -- init --apply asaf-kali
```

## Updating an existing machine

Pull latest from repo and apply (chezmoi already installed):

```sh
chezmoi update
```

## Common commands

```sh
chezmoi re-add           # sync from home into repo (no push)
chezmoi apply            # apply changes from repo to home
chezmoi diff             # preview pending changes
chezmoi cd               # shell into source dir
```
