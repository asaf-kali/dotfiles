# dotfiles

Managed with [chezmoi](https://www.chezmoi.io). See docs there.

## New machine setup

```sh
sh -c "$(curl -fsLS https://chezmoi.io/get)" -- init --apply asaf-kali
```

## Common commands

```sh
chezmoi update           # pull from repo + apply
chezmoi re-add           # sync from home into repo (no push)
chezmoi apply            # apply changes from repo to home
chezmoi diff             # preview pending changes
chezmoi cd               # shell into source dir
```
