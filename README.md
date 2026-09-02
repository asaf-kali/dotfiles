# dotfiles

Managed with [chezmoi](https://www.chezmoi.io).

## New machine

```sh
sh -c "$(curl -fsLS https://chezmoi.io/get)" -- init --apply asaf-kali
```

Installs chezmoi, clones this repo, applies the dotfiles, then installs packages, oh-my-zsh (with zsh
as login shell) and the auto-update timer.

## Existing machine

```sh
chezmoi update   # git pull in the source dir, then apply
```

Chezmoi's source dir is `~/.local/share/chezmoi` (`chezmoi source-path`) — possibly a different clone
than the one you edit in, so push first, then `chezmoi update`.

## Automatic system updates

`chezmoi apply` installs `/usr/local/sbin/system-update` (apt update + upgrade, snap refresh,
autoremove) and a systemd timer that runs it three times a day. The `update` alias runs the same script
by hand. Schedule lives in `.chezmoidata/auto_update.yaml` — edit and re-apply to change it.

```sh
systemctl list-timers system-update.timer   # when it next runs
journalctl -u system-update -n 100          # what happened last time
sudo systemctl start system-update.service  # run now, unattended-style
sudo systemctl disable --now system-update.timer
```

## Common commands

```sh
chezmoi diff     # preview pending changes
chezmoi apply    # apply source-dir state to $HOME
chezmoi re-add   # pull $HOME state back into the source dir
chezmoi cd       # shell into the source dir (~/.local/share/chezmoi)
```
