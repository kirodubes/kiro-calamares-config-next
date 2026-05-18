# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Role

**BETA / TESTING** — this is the experimental Calamares installer config, paired with `kiro-iso-next`.

| Repo | Role | ISO repo |
|---|---|---|
| `kiro-calamares-config` | **Production** — stable, released to users | `kiro-iso` |
| `kiro-calamares-config-next` | **Beta/Testing** — experimental changes under evaluation | `kiro-iso-next` |

Changes here must be tested with a full install run before being mirrored to `kiro-calamares-config`.
The current experiment: **Liquorix kernel** — `unpackfs2.conf` updated to copy `vmlinuz-linux-lqx`.

## Beta Build Workflow

**After making changes here, always follow this order:**

```
1. Commit and push: ./up.sh
2. Wait 5–10 minutes for kiro_repo (GitHub Pages) to rebuild and serve the updated package
3. Then trigger the ISO build in kiro-iso-next: cd ~/KIRO/kiro-iso-next/build-scripts && bash build-the-iso.sh
```

**Do not build the ISO immediately after pushing** — GitHub Pages needs a few minutes to rebuild. Building too soon pulls the old Calamares package and your changes won't be in the ISO.

## What This Is

Calamares installer configuration for the Kiro Linux distribution (Arch-based). Contains the full installation pipeline: module configs, custom Python extension modules, branding/QML slideshow, bundled microcode packages, and a custom Calamares PKGBUILD.

Part of the broader Kiro ecosystem:
- **kiro-pkgbuild** — upstream Calamares fork source (PKGBUILD edited there, not here)
- **kiro-iso** — ISO build scripts (sibling repo)
- **kiro-repo** — custom pacman repository at `https://kirodubes.github.io/$repo/$arch`

## Common Commands

```bash
# Commit and push all local changes
./up.sh

# First-time git remote setup (SSH alias git@github.com-edu)
./setup.sh

# Build Calamares (inside pkgbuild dir):
cd etc/calamares/pkgbuild && makepkg -si

# Run tests for the packages module:
cd etc/calamares/pkgbuild/modules/packages/tests && python -m pytest

# Run tests for the bootloader module:
cd etc/calamares/pkgbuild/modules/bootloader/tests && python -m pytest
```

There is no linter configured for this repo. The Python modules in `usr/lib/calamares/modules/` run inside a Calamares chroot at install time — they cannot be run standalone.

`up.sh` does: clean `__pycache__`, verify git remote is configured (runs `setup.sh` if not), `git pull`, then commit + push all changes. **Do not edit `etc/calamares/pkgbuild/PKGBUILD` here** — it must be edited in `~/KIRO/kiro-pkgbuild/` and copied manually.

## Installer Pipeline Architecture

**Entry point:** [etc/calamares/settings.conf](etc/calamares/settings.conf) — defines the full execution sequence.

**Show phase** (UI pages shown to user):
`welcome → locale → keyboard → partition → users → summary`

**Exec phase** (automated steps, in order):
```
partition → mount
→ unpackfs@rootfs → unpackfs@vmlinuz
→ machineid → locale → keyboard → localecfg
→ luksbootkeyfile → luksopenswaphookcfg
→ fstab → networkcfg
→ kiro_before → kiro_remove_nvidia
→ initcpiocfg → initcpio → hwclock
→ services-systemd → packages@choice
→ removeuser → users → displaymanager
→ kiro_ucode → grubcfg → bootloader
→ kiro_final → preservefiles → umount
```

**Finish phase:** `finished` page.

`unpackfs` and `packages` run as named instances (see `instances:` block in settings.conf): `rootfs` uses `unpackfs1.conf`, `vmlinuz` uses `unpackfs2.conf`, `choice` uses `packages.conf`.

## Custom Python Modules

All four live in [usr/lib/calamares/modules/](usr/lib/calamares/modules/). Each has a `main.py` and `module.desc`.

**Return convention:** all functions return `None` on success or a `(error_title, error_description)` tuple on failure. The `run()` entrypoint aggregates these. Non-fatal errors log via `libcalamares.utils.warning()` and do not abort the install.

| Module | Position in exec | Purpose |
|---|---|---|
| `kiro_before` | After networkcfg | Pacman lock wait, keyring init, mkinitcpio preset rename (`kiro` → `linux.preset`), makepkg optimization |
| `kiro_remove_nvidia` | After kiro_before | Reads `driver=` kernel param; **defaults to removing NVIDIA** unless `driver=nonfree` |
| `kiro_ucode` | After displaymanager | Detects CPU (AMD/Intel via hwinfo), installs bundled `.pkg.tar.zst` from `/etc/calamares/packages/` |
| `kiro_final` | Before preservefiles | Permissions, skel copy, live-only file cleanup, env config, bootloader cleanup, VM package removal, self-removal |

### kiro_remove_nvidia — default behaviour
`kernel_cmdline("driver", default="free")` — the default is `"free"`, so NVIDIA packages are removed unless the ISO is booted with `driver=nonfree` on the kernel cmdline. Packages checked: `nvidia-open-dkms`, `nvidia-utils`, `nvidia-settings`.

### VM Detection (kiro_final)
Uses `systemd-detect-virt` and removes packages for VMs you are **not** running in. The set-based logic:

| Detected VM | VMware tools removed? | QEMU agent removed? | VirtualBox utils removed? |
|---|---|---|---|
| `none` (bare metal) | yes | yes | yes |
| `vmware` | yes | yes | yes |
| `oracle` (VirtualBox) | yes | yes | no |
| `kvm` | yes | no | yes |
| `qemu` | no | no | no |

## Module Configs

All in [etc/calamares/modules/](etc/calamares/modules/). Key non-obvious settings:

- **partition.conf** — EFI min 2GB, swap as file (no partition), LUKS v1, auto-partitioning disabled
- **unpackfs1.conf / unpackfs2.conf** — two separate unpack steps (rootfs + kernel), with different weights (45 vs 5)
- **packages.conf** — removes `calamares`, `mkinitcpio-archiso`, `memtest86+`, `memtest86+-efi` after install; `skip_if_no_internet: false`

## Branding

[etc/calamares/branding/kiro/](etc/calamares/branding/kiro/) — dark theme, 1200×800 window, sidebar widget layout.

**Slideshow:** `show.qml` (QML API v2) cycles through `01cal.jpg`–`12cal.jpg`. To add/remove slides, edit both the QML and the image files. `show-backup.qml` is a fallback copy.

**Translations:** Qt `.ts` format in `lang/` — en, fr, nl, ar, eo.

## Microcode Bundling

Pre-downloaded `.pkg.tar.zst` files in [etc/calamares/packages/](etc/calamares/packages/) allow offline microcode installation. The `kiro_ucode` module finds them with `glob` on `/etc/calamares/packages/<vendor>-ucode-*.pkg.tar.zst` and installs via `pacman -U`.

When updating microcode: download the new package into `etc/calamares/packages/`, remove the old `.pkg.tar.zst` and `.sig` files, then commit.

## PKGBUILD Notes

[etc/calamares/pkgbuild/PKGBUILD](etc/calamares/pkgbuild/PKGBUILD) tracks a git snapshot of a Calamares fork on Codeberg (`https://codeberg.org/erikdubois/calamares`). It:
- conflicts with `calamares` and `calamares-git`
- provides `calamares-next`
- applies two patches in `prepare()`: enables config file installation (`"Install configuration files" OFF` → `ON`), increases fstab `desired_size` to 8589MiB (512×1024×1024×16)
- bundles the custom modules from `pkgbuild/modules/` (bootloader + packages overrides copied into the Calamares source tree)

**Do not edit the local PKGBUILD** — edit `~/KIRO/kiro-pkgbuild/` instead and copy manually.
