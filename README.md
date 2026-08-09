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

## Automatic system updates

`chezmoi apply` installs `/usr/local/sbin/system-update` (apt update + upgrade + snap
refresh + autoremove) and a systemd timer that runs it three times a day. The `update`
alias runs the same script by hand.

Schedule lives in `.chezmoidata/auto_update.yaml`; edit it and re-apply to change it.

```sh
systemctl list-timers system-update.timer   # when it next runs
journalctl -u system-update -n 100          # what happened last time
sudo systemctl start system-update.service  # run it now, unattended-style
sudo systemctl disable --now system-update.timer
```

## Common commands

```sh
chezmoi re-add           # sync from home into repo (no push)
chezmoi apply            # apply changes from repo to home
chezmoi diff             # preview pending changes
chezmoi cd               # shell into source dir
```
