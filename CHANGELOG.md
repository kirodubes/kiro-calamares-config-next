# CHANGELOG — kiro-calamares-config

> Calamares graphical installer configuration. Custom Python modules: `kiro_before`, `kiro_final`, `kiro_remove_nvidia`, `kiro_ucode`.

---

## 2026-05-26 — cups printing enabled on installed system (socket activation)

### What Changed

- **`services-systemd` now enables `cups.socket`.** Printing was off after a fresh install + reboot. The live ISO enabled CUPS via airootfs symlinks, but those are not carried into the installed system, and the Calamares `services-systemd` unit list (ananicy-cpp, tuned, tuned-ppd, firewalld) never enabled cups. Added a `cups.socket` → `enable` → `mandatory: true` entry. Socket activation only — `cups.service` starts on demand when a client opens the print socket, so there is no always-running daemon. Kept in sync with the production `kiro-calamares-config` fix; paired with `kiro-iso-next` trimming its airootfs cups symlinks to socket-only.

### Files Modified

- [etc/calamares/modules/services-systemd.conf](etc/calamares/modules/services-systemd.conf)

## 2026-05-26 — README: community framing, dropped "personal"

### What Changed

- **README no longer calls Kiro "my personal choice".** The defaults list (systemboot, ext4, sddm, xfce4 and chadwm, free software) is now introduced as "Kiro ships with opinionated defaults so it works out of the box" — community framing instead of the early single-user wording. Rule codified in [Kiro-HQ/ASSISTANT.md](../../Insync/Kiro/Kiro-HQ/ASSISTANT.md). README only; no installer behaviour changed, no rebuild needed.

## 2026-05-25 — kiro_final: remove live-only do-not-suspend.conf

### What Changed

- **`kiro_final` now removes `/etc/systemd/logind.conf.d/do-not-suspend.conf` on the installed system.** This drop-in (`HandleSuspendKey` / `HandleHibernateKey` / `HandleLidSwitch=ignore`) ships in the airootfs overlay so the live ISO does not suspend mid-install, but it was never cleaned up afterward — it persisted on every installed system and silently disabled suspend / hibernate / lid handling for end users (notably on laptops). Added it to the `paths_to_remove` list alongside the other live-only artifacts. Kept in sync with the production `kiro-calamares-config` fix.

### Technical Details

- One-line addition to `paths_to_remove` in `kiro_final/main.py`, grouped with the existing live-only cleanups (getty autologin, `linux.preset`, `10-archiso.conf`); reuses the existing `remove_path()` helper, so no change to the removal loop.
- Caught by `kiro-check` on an installed Kiro system. `kiro-audit` has no check for this file, so the leak had been passing the audit clean.

### Files Modified

- `usr/lib/calamares/modules/kiro_final/main.py`
- `CHANGELOG.md`

## 2026-05-22 — Silence "No config file" warnings for kiro_* modules

### What Changed

Added `noconfig: true` to the `module.desc` of all four custom Python modules: `kiro_before`, `kiro_final`, `kiro_remove_nvidia`, `kiro_ucode`. Mirrored from the same fix in `kiro-calamares-config` (production) — kept in sync so beta installs stay quiet too.

### Why

The fix originated from inspecting `/var/log/Calamares.log` on a production install: Calamares only searches `/etc/calamares/modules/<module>.conf` and `/usr/share/calamares/modules/<module>.conf` for module configs, never inside the module's own code directory. None of the four kiro modules actually reads any module-level config — they only use `libcalamares.globalstorage` and `libcalamares.utils`. The `noconfig: true` flag in `module.desc` ([Descriptor.cpp:96](https://codeberg.org/erikdubois/calamares/src/branch/master/src/libcalamares/modulesystem/Descriptor.cpp#L96), [ModuleManager.cpp:165](https://codeberg.org/erikdubois/calamares/src/branch/master/src/libcalamaresui/modulesystem/ModuleManager.cpp#L165)) tells Calamares to skip the config lookup entirely — the truthful, zero-maintenance fix.

### Technical Details

- `noconfig: true` was appended to each of the four `module.desc` files; the indentation matches the existing keys (the `kiro_ucode` descriptor uses padded alignment, the others do not).
- No dummy `.conf` files existed in `-next` so no deletions were required here (production had four misplaced dummies that were deleted in its companion commit).

### Files Modified

- `usr/lib/calamares/modules/kiro_before/module.desc`
- `usr/lib/calamares/modules/kiro_final/module.desc`
- `usr/lib/calamares/modules/kiro_remove_nvidia/module.desc`
- `usr/lib/calamares/modules/kiro_ucode/module.desc`

---

## 2026-05-19 — Liquorix Kernel Experiment Validated and Promoted to Production

### What Changed

The Liquorix kernel experiment that originated in this repo has been declared stable and fully mirrored to `kiro-calamares-config` (production). Kiro now ships `linux-lqx` as the default installed kernel on both the stable and beta ISO tracks.

### Why

The Liquorix kernel (`linux-lqx`) is a patched Linux kernel targeting desktop responsiveness and low latency. By shipping it as the default, Kiro users get improved desktop performance without any manual post-install steps. The beta track validated the installer pipeline handles `linux-lqx` correctly end-to-end before it went to production.

### Technical Details

Seven files were reviewed for promotion. Four were copied verbatim; one required a package-name correction; two were left unchanged because each repo correctly references its own package name.

**Files promoted to `kiro-calamares-config`:**

- **`unpackfs2.conf`** — updated source from `vmlinuz-linux` to `vmlinuz-linux-lqx` and destination from `/boot/vmlinuz-linux` to `/boot/vmlinuz-linux-lqx`. This is the step that physically copies the kernel binary into the installed target root.
- **`kiro_before/main.py`** — the mkinitcpio preset rename now targets `linux-lqx.preset` instead of `linux.preset`. The preset filename must match the kernel package name so mkinitcpio knows which config to use when generating the initramfs.
- **`kiro_final/main.py`** — two improvements merged: (1) `linux.preset` added to the live-only artifact cleanup list, because the archiso environment ships a `linux.preset` for the live system that would otherwise persist into the installed target and conflict with the `linux-lqx.preset` from the kernel package; (2) self-removal pacman command corrected from `kiro-calamares-config-next` to `kiro-calamares-config` (production package name).
- **`kiro_ucode/main.py`** — new `remove_ucode_package()` method added. Previously, the correct microcode was installed but the wrong one (the other vendor's package) could remain on disk. Now the module installs the matching microcode and explicitly removes the non-matching one, keeping the installed system clean.
- **`displaymanager.conf`** — trailing newline normalised (cosmetic).

**Files left at their production values:**

- **`packages.conf`** — removes `calamares` at the end of install (not `calamares-next`). Each repo removes its own package.
- **`PKGBUILD`** — `pkgname=calamares` in production, `pkgname=calamares-next` in this repo. Not changed.

A post-promotion grep scan of the production repo confirmed no stale `-next` references survived in code or config. Legitimate occurrences (Python `__next__`, `provides=('calamares-next')` virtual package, Calamares config key `hide-back-and-next-during-exec`) were verified as intentional.

### Workflow Corrections Logged

Two standing rules were added to memory this session:

1. Always grep production repo for `-next` after any promotion before committing.
2. The calamares config repo always pairs with its matching ISO repo — `kiro-calamares-config-next` → `kiro-iso-next`, never `kiro-iso`.

### Files Modified

- `etc/calamares/modules/unpackfs2.conf`
- `etc/calamares/modules/displaymanager.conf`
- `usr/lib/calamares/modules/kiro_before/main.py`
- `usr/lib/calamares/modules/kiro_final/main.py`
- `usr/lib/calamares/modules/kiro_ucode/main.py`
- `CHANGELOG.md` (this file)
- `TODO.md` — active items marked done
- `IDEAS.md` — stub created
- `~/.claude/projects/.../memory/` — two new memory files written

---

## 2026-04-26
- **`amd-ucode`** package updated → `20260410-1`

---

## 2026-04-15 — Major Module Rewrite Day

### Python Modules
- **`kiro_before/main.py`** — 40+22+8 lines added across 3 commits; expanded pre-install setup logic
- **`kiro_final/main.py`** — 335+171 lines changed across 2 commits; major post-install logic rewrite
- **`kiro_remove_nvidia/main.py`** — 19+11 lines changed; improved Nvidia removal logic
- **`kiro_ucode/main.py`** — 48 lines added (expanded microcode detection), then 6 lines fixed

### Installer Flow
- **Removed `kiro-postinstall`** script (141 lines) — logic fully absorbed into `kiro_final`
- **Removed `shellprocess-final.conf`** + its `settings.conf` entries — now handled natively
- **Removed `pacman-init.service`** symlink — no longer needed at install time
- **`__pycache__`** binaries removed from repo

### Bundled Microcode
- **`intel-ucode-20260227-1`** added as bundled `.pkg.tar.zst`
- **`amd-ucode-20260309-1`** updated
- **`unpackfs2.conf`** updated to reference new ucode paths

### `up.sh`
- Rewritten from 5 → 60 lines — now handles full build-and-deploy flow

---

## 2026-04-14 — Slideshow Overhaul

- **Removed** 3 branding slides (`02cal`, `03cal`, `04cal`) — large originals
- **Replaced** `show.qml` with `show-backup.qml` (209-line full QML slideshow with transitions)
- **Compressed** remaining slides (`09cal`, `10cal`, `11cal`, `12cal`)

---

## 2026-04-09
- **`pkgbuild/`** — added bootloader module schema, tests, `test.yaml`
- **`branding.desc`** — updated product info
- **`up.sh`** — updated

---

## 2026-04-05
- **Branding slides** `06cal`, `07cal`, `08cal` — re-compressed (significant size reduction)

---

## 2026-01-31
- **`kiro_remove_nvidia/main.py`** — expanded (+24 lines), improved detection logic
- **`unpackfs1/2.conf`** — reordered unpack sequences
- **`settings.conf`** — module order updated

---

## 2026-01-11
- **`PKGBUILD`** — version bump, dependency update
- **`packages/main.py`** — minor fix

---

## 2025-12-21
- **`kiro_remove_nvidia/main.py`** — single-line fix

---

## 2025-11-29
- **Branding slides** `01–08cal` — rotated/replaced (6 slides swapped)

## 2025-11-28
- **`partition.conf`** — updated partition layout settings

---

## 2025-11-26
- **`pkgbuild/bootloader/main.py`** — added (966 lines) — custom bootloader module

---

## 2025-11-08/09 — Module Cleanup

- **Removed `displaymanager` module** from pkgbuild (1053-line `main.py`, schema, tests — all gone)
- **`displaymanager.conf`** added to `modules/` (now uses upstream module)
- **`unpackfs1.conf`** — removed (simplified to single unpack)
- **`settings.conf`** — updated module pipeline

---

## 2025-10-21
- **`PKGBUILD`** — version bump

## 2025-10-09
- **Branding** `01cal`, `05cal`, `08cal` — compressed
- **`up.sh`** — rewritten with deploy logic

---

## 2025-07-16 — Full Slideshow Added

- **Added 11 branding slides** (`01cal` through `12cal`) — complete installer slideshow
- **`show.qml`** — rewritten (134 lines) — proper QML slideshow with timed transitions

---

## 2025-07-07
- **`bootloader.conf`** — updated bootloader settings
- **`partition.conf`** — 2 settings added

## 2025-07-03
- **`PKGBUILD`** — significant refactor
- **`build-calamares`** — renamed from `.sh`, logic updated
- **`up.sh`** — rewritten (30 lines changed)

## 2025-07-01
- **`settings.conf`** — module pipeline reordered

---

## 2025-06-25 — PKGBUILD & Wrapper Cleanup

- **Removed `cal-kiro-debugging.desktop`** — debug launcher gone
- **Added `calamares-wrapper`** — proper launch wrapper (38 lines)
- **`PKGBUILD`** — refactored (25 lines changed)
- **Renamed** `calamares-3.3.14.r25.g95aa33f/` → `pkgbuild/` (cleaner folder name)
- **Removed `ucode` module** from pkgbuild (59-line `main.py` gone — now `kiro_ucode` handles it)

---

## 2025-06-24 — Custom Modules Born

All four `kiro_*` Python modules added:
- **`kiro_before/main.py`** — 122 lines — pre-install setup
- **`kiro_final/main.py`** — 304 lines — post-install finalization
- **`kiro_remove_nvidia/main.py`** — 74 lines — Nvidia driver removal
- **`kiro_ucode/main.py`** — 57 lines — CPU microcode installation
- **`pacman-init.service`** added (keyring init at install time)
- **`settings.conf`** simplified — removed many upstream modules
- Added helper scripts: `add-kiro-repo`, `dev`, `kiro-postinstall` (141 lines), `qdd-kiro-repo`

---

## 2025-06-20
- **`services-systemd.conf`** module added (57 lines) — systemd service enable/disable list

---

## 2025-05-29 — Alternate Config Cleanup

- **Removed** all "alternate settings" files: `settings-advanced-remove.conf`, `settings-beginner-remove.conf`, `settings-advanced-no-nivida-remove.conf`
- **Removed** offline/online shellprocess-before variants
- **Renamed** partition/packages configs to `-remove` suffix (cleanup pass)

---

## 2025-05-28 — ArcoLinux Removal

- **Removed all `arcolinux-*` binaries** from `usr/local/bin/` (21 scripts, ~1100 lines total):
  - `arcolinux-all-cores`, `arcolinux-before`, `arcolinux-displaymanager-check`
  - `arcolinux-nvidia-settings` (304 lines), `arcolinux-graphical-target` (60 lines)
  - `arcolinux-virtual-machine-check` (191 lines), `arcolinux-set-bootloader` (87 lines)
  - `arconet-remove-xfce`, `arcopro-remove-sddm`, `arcopro-remove-xfce`, etc.
- **Removed** bundled bootloader `.pkg.tar.zst` files
- **`pacman-init.service`** removed from systemd wants
- All files moved under `etc/calamares/` (was at root `calamares/`)

---

## 2025-05-17 — Build System Bootstrap

- **PKGBUILD** — multiple iterations finalizing calamares build config
- **`build-calamares`** — rewritten from scratch (35→13 line simplification)
- **`.gitignore`** — binary artifacts excluded

---

## 2025-04-29
- **`settings.conf`** — expanded with advanced/beginner/LUKS config variants
- **`unpackfs1/2.conf`** — dual-unpack setup

---

## 2025-04-27 — Initial Commit

- **Full Calamares config bootstrapped** (55 files, 2026 insertions)
  - Branding: `kiro/` theme with logo, stylesheet, language files, 9 slide images
  - Modules: all standard Calamares modules configured
  - Settings: beginner + advanced installer flows
  - PKGBUILD for custom Calamares build
