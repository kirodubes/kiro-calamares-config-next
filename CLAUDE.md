# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Role

**BETA / TESTING** — this is the experimental Calamares installer config, paired with `kiro-iso-next`.

| Repo                         | Role                                                     | ISO repo        |
|------------------------------|----------------------------------------------------------|-----------------|
| `kiro-calamares-config`      | **Production** — stable, released to users               | `kiro-iso`      |
| `kiro-calamares-config-next` | **Beta/Testing** — experimental changes under evaluation | `kiro-iso-next` |

Changes here must be tested with a full install run before being mirrored to `kiro-calamares-config`.

**Current experiment:** `packages.conf` `update_db: false` — stop a failing `pacman -Sy` from aborting the install at ~99% (kiro-discussions #10). Needs a full offline install run before mirroring to production.

## Beta Build Workflow

**After making changes here, always follow this order:**

```
1. Push config source:  cd ~/KIRO-ISO-CALAMARES/kiro-calamares-config-next && ./up.sh
2. Build the package:    cd ~/KIRO-PKG-BUILD-CALAMARES/kiro-calamares-config-next && bash build.sh
                         (pulls the just-pushed config, builds via chroot, drops the
                          .pkg.tar.zst into ~/KIRO/kiro_repo/x86_64/)
3. Publish the repo:     cd ~/KIRO/kiro_repo && ./repo.sh && ./up.sh
                         (repo.sh regenerates the pacman db, up.sh pushes to GitHub Pages)
4. Wait 5–10 minutes for kiro_repo (GitHub Pages) to serve the new package
5. Build the ISO:        cd ~/KIRO-ISO-CALAMARES/kiro-iso-next/build-scripts && bash build-the-iso.sh
6. Full install run to validate
```

**Steps 2–3 are mandatory** — `up.sh` here only pushes the config *source* to GitHub. The
Calamares config is repackaged from that GitHub repo by `build.sh` in `KIRO-PKG-BUILD-CALAMARES`, and the
resulting package only reaches the ISO after `kiro_repo` is regenerated and pushed to GitHub Pages.

**Do not build the ISO immediately after step 3** — GitHub Pages needs a few minutes to rebuild.
Building too soon pulls the old Calamares package and your changes won't be in the ISO.

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

`up.sh` does: clean `__pycache__`, verify git remote is configured (runs `setup.sh` if not), `git pull`, then commit + push all changes. **Do not edit `etc/calamares/pkgbuild/PKGBUILD` here** — it must be edited in `~/KIRO-PKG-BUILD-CALAMARES/` and copied manually.

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

| Module               | Position in exec     | Purpose                                                                                                          |
|----------------------|----------------------|------------------------------------------------------------------------------------------------------------------|
| `kiro_before`        | After networkcfg     | Pacman lock wait, keyring init, mkinitcpio preset rename (`kiro` → `linux.preset`), makepkg optimization     |
| `kiro_remove_nvidia` | After kiro_before    | Reads `driver=` kernel param; removes NVIDIA on `free` + `nonfreechwd`, keeps the baked `nvidia-open-dkms` on `nonfree` |
| `chwd`               | After kiro_remove_nvidia | Runs `chwd --autoconfigure` **only** on `driver=nonfreechwd`; first leads cachyos/chaotic with a trusted geo-CDN mirror + `pacman -Sy` (best-effort), then picks the right driver for the detected GPU |
| `kiro_ucode`         | After displaymanager | Detects CPU (AMD/Intel via hwinfo), installs bundled `.pkg.tar.zst` from `/etc/calamares/packages/`              |
| `kiro_final`         | Before preservefiles | Permissions, skel copy, live-only file cleanup, env config, bootloader cleanup, VM package removal, self-removal |

### NVIDIA driver modes (`driver=` kernel cmdline)
`kernel_cmdline("driver", default="free")`. Three modes drive `kiro_remove_nvidia` + `chwd` (packages checked: `nvidia-open-dkms`, `nvidia-utils`, `nvidia-settings`):
- **`free`** (default) — `kiro_remove_nvidia` removes the NVIDIA packages; chwd skipped → mesa / open stack.
- **`nonfree`** — both modules skip; the baked `nvidia-open-dkms` is kept untouched (proven express lane for modern Turing+ GPUs).
- **`nonfreechwd`** — `kiro_remove_nvidia` removes the baked NVIDIA packages first (clean slate), then `chwd --autoconfigure` installs exactly the profile it detects (any card) with nothing to conflict. This is the **only online install path** (driver comes mainly from `[cachyos]`, some from `[chaotic-aur]`), so the chwd module first leads both mirrorlists with a trusted geo-CDN server (the same ones `build-scripts/host-prep.sh` uses) and runs `pacman -Sy` to refresh the chroot's stale sync DBs — both best-effort, never fatal.

### VM Detection (kiro_final)
Uses `systemd-detect-virt` and removes packages for VMs you are **not** running in. The set-based logic:

| Detected VM           | VMware tools removed? | QEMU agent removed? | VirtualBox utils removed? |
|-----------------------|-----------------------|---------------------|---------------------------|
| `none` (bare metal)   | yes                   | yes                 | yes                       |
| `vmware`              | yes                   | yes                 | yes                       |
| `oracle` (VirtualBox) | yes                   | yes                 | no                        |
| `kvm`                 | yes                   | no                  | yes                       |
| `qemu`                | no                    | no                  | no                        |

## Module Configs

All in [etc/calamares/modules/](etc/calamares/modules/). Key non-obvious settings:

- **partition.conf** — EFI min 2GB, swap as file (no partition), LUKS v2 (grub now unlocks LUKS2/Argon2id via GRUB 2.14), `defaultPartitionTableType` empty so Calamares auto-picks gpt on UEFI / msdos on BIOS, auto-partitioning disabled
- **unpackfs1.conf / unpackfs2.conf** — two separate unpack steps (rootfs + kernel), with different weights (45 vs 5)
- **packages.conf** — removes `calamares`, `mkinitcpio-archiso`, `memtest86+`, `memtest86+-efi` after install; `skip_if_no_internet: false`

## Branding

[etc/calamares/branding/kiro/](etc/calamares/branding/kiro/) — dark theme, 1200×800 window, sidebar widget layout.

**Slideshow:** `show.qml` (QML API v2) is a text-based slideshow — inline `KiroTitleSlide` / `KiroSlide` components, no screenshots. To add/remove slides, edit the slide blocks in the QML. The `01cal.jpg`–`12cal.jpg` images are unused by the current QML.

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

**Do not edit the local PKGBUILD** — edit `~/KIRO-PKG-BUILD-CALAMARES/` instead and copy manually.
