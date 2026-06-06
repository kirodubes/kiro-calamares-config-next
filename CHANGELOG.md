# CHANGELOG — kiro-calamares-config

> Calamares graphical installer configuration. Custom Python modules: `kiro_before`, `kiro_final`, `kiro_kernel`, `kiro_remove_nvidia`, `kiro_ucode`.

---

## 2026-06-05 — LUKS2 default + firmware-correct partition table

**What Changed**
- **`partition.conf`**: `luksGeneration: luks1 → luks2`.
- **`partition.conf`**: `defaultPartitionTableType: gpt → ""` (empty) → Calamares auto-picks **gpt on UEFI, msdos on BIOS**.

**Why**
- GRUB 2.14 (Arch `grub 2:2.14-1`) added Argon2i/Argon2id KDF support → GRUB unlocks LUKS2/Argon2id, so luks1-on-grub is no longer needed.
- Empty partition-table is the required companion: hardcoded `gpt` crashes legacy-BIOS GRUB installs (no `bios_grub` partition). Empty gives BIOS an MBR, UEFI a GPT+ESP.
- **Tested here first**: BIOS+grub+luks2 (*worf*) and UEFI+grub+luks2 (*picard*) both booted with GRUB unlocking the LUKS2/Argon2id volume. Then ported to production `kiro-calamares-config`. See the nemesis CTT fork's `GRUB+LUKS2.md`.

---

## 2026-06-03 — systemd initramfs hooks, so the encrypted-boot LUKS prompt is visible

**What Changed**
- **New `etc/calamares/modules/initcpiocfg.conf`** with `useSystemdHook: true` (+ `source: /etc/mkinitcpio.conf`).
- **`settings.conf`**: removed `kiro_plymouth` from the exec sequence (now redundant).
- **Deleted the `usr/lib/calamares/modules/kiro_plymouth/` module dir entirely** — not just unwired. It was redundant with stock `initcpiocfg` *and* buggy: it inserted `plymouth` only after a `udev` hook (`re.sub(r"\budev\b", "udev plymouth", …)`) and silently no-op'd on any `systemd`-based HOOKS line — the precise reason the LUKS prompt stayed text on the systemd-hook installs.

**Why**
- On an encrypted install the LUKS passphrase prompt was **invisible / bare text at boot** (user had to type it blind), on ext4/btrfs alike. The busybox `encrypt` hook prompts through the kiro-logo Plymouth theme's script `DisplayPasswordCallback`, which doesn't render reliably at boot. Switching to the **systemd hooks** (`systemd` + `sd-encrypt`) makes `sd-encrypt` ask via `systemd-ask-password`, which Plymouth's **built-in password agent** renders reliably as a themed prompt — exactly how CachyOS ships Plymouth + encryption (`useSystemdHook: true`, reference: `~/Documents/cachyos-calamares` → `settings.conf` lists `plymouthcfg`).
- The rest cascades automatically in Calamares (verified @ g841b478): `initcpiocfg` itself adds the `plymouth` hook via `detect_plymouth()` **before** the encrypt hook — for both `sd-encrypt` and `encrypt` (so `kiro_plymouth` is redundant), and `bootloader/main.py` detects the systemd HOOKS and writes `rd.luks.uuid=…` instead of `cryptdevice=…`, plus `splash`. One flag, whole chain.
- **Validated on the Kiro-next VM** (hand-patched booted state, not yet a fresh install): with `plymouth` present before `sd-encrypt` in the *booted* initrd, the graphical login card renders correctly. Key gotcha for the build: the booted initrd is the BLS/kernel-install copy in the ESP, NOT the loose `/boot/initramfs-*.img` — see [HQ/RESUME.md](../../../Insync/Kiro/Kiro-HQ/RESUME.md).
- Tradeoff: no busybox emergency recovery shell. **Switches ALL installs to the systemd initramfs** — test encrypted AND plain installs.
- **Beta only** — this is `kiro-calamares-config-next`; production `kiro-calamares-config` is untouched (zero risk to the mainstream ISO) until a passing **fresh encrypted test-install** (confirming `detect_plymouth()` fires, i.e. plymouth is installed in the target before `initcpiocfg` runs). Port to production only after that passes.

---

## 2026-06-03 — qdd-kiro-repo: make adding the Kiro repo idempotent

**What Changed**
- `usr/local/bin/qdd-kiro-repo`: guard the append with `grep -q '^\[kiro_repo\]'` — only add the `[kiro_repo]` section if it isn't already in `/etc/pacman.conf`.

**Why**
- The script did a blind `tee --append`, so running it on a system that already had the repo (it's baked into the ISO `pacman.conf`) wrote a **second** `[kiro_repo]` section. pacman then fails every transaction with *"could not register 'kiro_repo' database (database already registered)."* Seen live on a kiro-iso-next VM. The grep guard makes a duplicate impossible no matter how often it runs. (Personal dev utility — bare style like `dev`, not the full bash template; see TEMPLATE_EXCLUSIONS rationale.)

---

## 2026-06-01 — packages: disable update_db so a failing `pacman -Sy` no longer aborts the install

**What Changed**
- `packages.conf`: `update_db: true` → `false`.

**Why**
- A user (kiro-discussions #10) hit *"Package Manager error — the command pacman returned error code 1 / could not prepare updates"* at ~99% on bare metal, on both NVIDIA boot entries. Traced to the Calamares `packages@choice` module's `update_db: true`: it runs a `pacman -Sy` on **every** install (driver-independent — the `nonfree` path downloads no driver), and with `skip_if_no_internet: false` a failed `-Sy` (no internet, or an unreachable mirror in the live `pacman.conf`) is **fatal**. VMs passed only because NAT gave them internet.
- The module's real work is the `try_remove` of the live-only packages, and `pacman -R` needs no synced DB. DB freshness is already handled best-effort (and non-fatally) by `kiro_before.sync_pacman_databases()`. So disabling `update_db` removes the abort with no real loss.

**Testing**
- Needs a full offline install run (no network in the live session) to confirm the install completes and live packages are still removed. Test in -next, then mirror to production.

**Files Modified**
- `etc/calamares/modules/packages.conf`

## 2026-05-31 — Three NVIDIA driver modes (free / nonfree / nonfreechwd) — mirrored from production

**What Changed**
- Mirrors kiro-calamares-config: `kiro_remove_nvidia` removes the baked NVIDIA packages on `free` **and** `nonfreechwd`; plain `nonfree` keeps `nvidia-open-dkms` untouched. `chwd` runs **only** on `nonfreechwd`.

**Why**
- `nonfree` = chwd-free express lane to the baked `nvidia-open-dkms` (modern Turing+); `nonfreechwd` wipes the baked driver first so chwd installs its detected profile with nothing to conflict (fixes the older-card `470xx`/`390xx` collision).

**Files Modified**
- `usr/lib/calamares/modules/kiro_remove_nvidia/main.py`
- `usr/lib/calamares/modules/chwd/main.py`
- `CLAUDE.md`

## 2026-05-29 — Dark installer: KiroDark Kvantum theme + dark branding

**What Changed**

Made the Calamares installer fully **dark**, matching the Kiro website (navy `#0F172A` background, sky-blue `#0EA5E9` accent) instead of the light-grey default. Root cause of the grey: the installer launched with `-style breeze`, but the `breeze` style was never installed, so Qt fell back to its light default. Fix: a custom **KiroDark** Kvantum theme launched via `-style kvantum` (kvantum is already on the ISO — zero new runtime deps). Branding updated for dark: sidebar selected-step highlight to brand blue with white text, nav-button **hover** text to white (it was an unreadable blue-on-light), combo/list/tree selections to brand blue, and a dark-navy K for the welcome logo + window icon.

**Technical Details**

- **KiroDark** = the ArcDark Kvantum theme with its palette remapped to Kiro (greys → navy, Arc blue `#5294e2` → `#0ea5e9`), forced **opaque** (`translucent_windows=false`, `reduce_window_opacity=0` — translucency bled the wallpaper through dense pages like Summary), and white button text (`[PanelButtonCommand]` `text.normal/focus/press/toggle=#ffffff`). It ships in the ISO at `/root/.config/Kvantum/KiroDark/` (Calamares runs as root via pkexec, so it reads root's config) and is selected by `/root/.config/Kvantum/kvantum.kvconfig` → `theme=KiroDark`.
- **branding.desc**: `SidebarTextHighlight #0EA5E9`, `SidebarSelect #FFFFFF`, `productIcon` + `productWelcome` → `welcome.png` (dark-navy K, blends into the panel — no white box).
- **stylesheet.qss**: accent `#0EA5E9` → `#0284C7`; nav-button `:hover` color → `#FFFFFF` (fixes the blue-on-light mush); list/combo/tree selections → white text on `#0284C7`.
- The previously light panel surfaces (e.g. Summary section headers) are now handled by the dark Qt **style**, not per-widget QSS hacks.
- Validated live on the beta VM via an SSH loop (edit theme → relaunch Calamares as root on `:0` → screenshot).
- `kiro_final` now removes `root/.config/Kvantum` from the target — the KiroDark theme styles the installer (run as root) but is live-only cruft on the installed system.

**Files Modified**
- `etc/calamares/branding/kiro/stylesheet.qss`
- `etc/calamares/branding/kiro/branding.desc`
- `etc/calamares/branding/kiro/welcome.png` (new)
- `usr/lib/calamares/modules/kiro_final/main.py`

**Cross-repo:** `kiro-iso-next` ships the KiroDark theme + `kvantum.kvconfig` under `airootfs/root/.config/Kvantum/` and adds `kvantum` to `packages.x86_64`. The launcher change (drop `calamares-wrapper`; set `cal-kiro.desktop` `Exec` → `calamares_polkit -d -style kvantum`) is handled in the KIRO-PKG-BUILD `calamares-next` source.

## 2026-05-29 — Installer visual refresh: brand-aligned chrome + text slideshow

**What Changed**

Gave the Calamares branding a "shining" pass so the installer chrome matches the brand instead of fighting it, and replaced the slideshow with professional brand text slides. The old slideshow cycled nine static Kiro-website screenshots (near-black slate, vivid sky-blue accent), while the surrounding installer used a medium-grey sidebar (`#353945`) and a muted blue accent (`#58B2D7`) — so the frame and the slides looked like two different products. The chrome now uses the website's own palette (sky `#0EA5E9`/`#38BDF8` accent, slate-900 sidebar), and the slideshow is a custom QML text deck — kicker, headline, gradient divider and a few short feature lines per slide on the slate gradient backdrop — with every line sourced from the website feature list.

**Technical Details**

- **branding.desc** — `SidebarBackground` `#353945` → slate-900 `#0F172A`; `SidebarText` → slate-200 `#E2E8F0`. Only the two proven keys were touched (selected-step highlight still falls back to the app palette).
- **stylesheet.qss** — every flat `#58B2D7` (selections, tooltip, progress chunk, scrollbar handle, combo/tree/list highlights) → brand `#0EA5E9` (accent-500, good contrast with white text); the three nav-button `:hover` states use the brighter `#38BDF8` (accent-400). `#sidebarMenuApp` background matched to `#0F172A`; the jarring light `#efefef` scrollbar track darkened to slate-800 `#1E293B`.
- **show.qml / show-backup.qml** — rewritten from a 9-image screenshot loop to a text slideshow: a `z: -1` slate gradient backdrop (`#020617`→`#0F172A`), two inline QML components (`KiroTitleSlide`, `KiroSlide`) for a DRY layout, and 7 slides (title → Pure Arch / Software / Performance / Desktop / Security → "Enjoy Kiro"). Headlines `#F1F5F9`, sky kicker `#38BDF8`, slate body `#CBD5E1`, blue→green gradient dividers, opacity fade-in per slide, 6.5 s auto-advance. No author byline (the website's "creator of ArcoLinux" is stale vs. the current "creator of Kiro"). The `01–12cal.jpg` screenshots are now unused by the QML.
- Rendered and verified on the dev box via the locally-built Calamares fork — see `~/.bin/kiro-calamares-preview.sh`.

**Files Modified**
- `etc/calamares/branding/kiro/branding.desc`
- `etc/calamares/branding/kiro/stylesheet.qss`
- `etc/calamares/branding/kiro/show.qml`
- `etc/calamares/branding/kiro/show-backup.qml`

**Addendum — marketing pass: slide deck expanded 7 → 16, plain-language rewrite**

Did a marketeer pass over the deck: positioning and app slides added, all copy verified against the repo (no invented features — encryption is *not* claimed; partition.conf has `enableLuksAutomatedPartitioning: false`).

- New slides: "Arch Linux, with a teacher in the box" (open/teachable), "Use Kiro today, master Linux for life." (learn & grow), per-app slides for **ATT** (*"Your Arch, one click at a time."*), **alacritty-tweak-tool** (*"Point, click, done. Your terminal, dialled in."*), **Archlinux-logout** (*"Go out in style."*), **Hardware** (*"Detects your hardware. Sorts the rest."* — microcode/NVIDIA/VM-cleanup), **Design** (*"Eye candy, out of the box."*), **Rollback** (*"Break something? Roll back in minutes."* — Timeshift), and "Stuck? There's already a video for that."
- **Performance** slide rewritten from kernel jargon (linux-cachyos, BBR, zram, ananicy-cpp) to plain benefits ("Faster boot, snappier apps, smoother under heavy load").
- De-duplicated: moved Timeshift off the Security slide into its own Rollback slide; dropped the "themed/no ricing" line from Desktop now that Design owns it.
- Removed the unreferenced `show-backup.qml` (branding.desc uses only `show.qml`).

---

## 2026-05-29 — `[cachyos]` repo disabled by default on the installed system

**What Changed**

`kiro_final` now comments out the `[cachyos]` repo (header + its `Include` line) in the target `/etc/pacman.conf` at the end of the install. cachyos stays **enabled during** the install (chwd pulls its driver packages from it) and is only disabled afterward; keyring + mirrorlist remain installed, so a user re-enables it by uncommenting the two lines.

Rationale: keeps `pacman -Syu` from silently swapping base packages for cachyos-optimized rebuilds. Safe for the default kernel because `chaotic-aur` stays enabled and carries `linux-cachyos`/`-headers`. (If `chaotic-aur` is ever dropped, revisit — cachyos would become the sole source for `linux-cachyos`.)

**Technical Details**

- [usr/lib/calamares/modules/kiro_final/main.py](usr/lib/calamares/modules/kiro_final/main.py) — new private `_disable_repo(target_root, repo)` helper (idempotent; comments header + body until a blank line or next `[section]`), called for `cachyos` after the tuned pin and before bootloader config — well after chwd in the exec sequence.
- chwd skip-marker text updated to tell users to uncomment `[cachyos]` if a driver package can't be found.
- Identical to the change mirrored into production [kiro-calamares-config](../kiro-calamares-config/CHANGELOG.md) the same date (kiro_final differs only in its own self-removal package name).

**Files Modified**
- `usr/lib/calamares/modules/kiro_final/main.py`
- `usr/lib/calamares/modules/chwd/main.py`

## 2026-05-29 — chwd failure is now non-fatal (install no longer aborts)

**What Changed**

On a laptop install, `chwd --autoconfigure` selected a driver profile whose package set included a package that none of the configured target repos carried. pacman aborted the transaction, the chwd module returned a `(error_title, error_description)` tuple, and Calamares **aborted the whole installation** — leaving the user with no installed system over a missing driver package.

The chwd module now treats a chwd failure as **non-fatal**. When `chwd --autoconfigure` exits non-zero, the module logs a `libcalamares.utils.warning`, writes a breadcrumb to `/var/log/kiro-chwd-skipped.log` on the target, and returns `None` so the install completes on the open driver (nouveau/mesa, already in the ISO). Safe because pacman transactions are atomic (a missing target installs nothing) and chwd's own `pre_remove` hook removes any mkinitcpio drop-ins it had written, so a failed run leaves no half-configured state.

This change is identical to the one mirrored into production [kiro-calamares-config](../kiro-calamares-config/CHANGELOG.md) on the same date (the chwd `main.py` is byte-identical across both trees).

**Technical Details**

- [usr/lib/calamares/modules/chwd/main.py](usr/lib/calamares/modules/chwd/main.py) — `run()` no longer returns the error tuple from `run_in_host`; on failure it warns, calls the new private `_record_skip(root_mount_point, detail)` helper, sets progress to 1.0, and returns `None`.
- `_record_skip` writes `/var/log/kiro-chwd-skipped.log` (reason + retry hint) into the chroot; an `OSError` while writing is itself non-fatal (warn only).
- Surfaced post-install by `kiro-audit`'s new `check_chwd` ([edu-system-files](/home/erik/EDU/edu-system-files/CHANGELOG.md)).

**Files Modified**
- `usr/lib/calamares/modules/chwd/main.py`

## 2026-05-28 — Hardware-aware install via **chwd**: new Calamares module (paired with `kiro-iso-next`)

First step of the install-time driver-selection experiment. The companion change in [kiro-iso-next](../kiro-iso-next/) added `chwd`, `b43-fwcutter`, `broadcom-wl-dkms`, and `hwdetect` to the live ISO. This repo provides the Calamares wiring that actually invokes chwd during install.

### What Changed

**New module: `usr/lib/calamares/modules/chwd/`**

Two-file Python jobmodule pattern, modelled after CachyOS's own `cachyos-calamares/src/modules/chwd/`:

- **[module.desc](usr/lib/calamares/modules/chwd/module.desc)** — five-line descriptor declaring this as a Python `job` module pointing at `main.py`.
- **[main.py](usr/lib/calamares/modules/chwd/main.py)** — runs `arch-chroot $rootMountPoint chwd --autoconfigure` inside the target chroot. chwd then inspects PCI/USB devices, picks the highest-priority matching TOML profile per device class, and installs the right driver bundle (NVIDIA 470xx / 580xx / nvidia-open-dkms / nouveau / AMD / Intel / Broadcom Wi-Fi / hybrid PRIME variants for laptops detected via DMI chassis types 8/9/10/11). Output is piped into the Calamares debug log via `libcalamares.utils.debug` with a `chwd:` prefix for traceability.

The module **honours the existing GRUB-menu `driver=` kernel cmdline**: when `driver=free` is set, `kernel_cmdline()` returns `"free"` and chwd is skipped entirely — `kiro_remove_nvidia` has already removed proprietary NVIDIA at that point, and nouveau ships in the kernel. Only `driver=nonfree` (or no `driver=` at all) triggers chwd's hardware-detection run.

**Settings.conf — chwd added to exec sequence**

[etc/calamares/settings.conf](etc/calamares/settings.conf) line 36: `chwd` inserted between `kiro_remove_nvidia` and `initcpiocfg`. The position matters: DKMS modules that chwd installs need to be in place before `initcpiocfg` writes the mkinitcpio preset and `initcpio` regenerates the initramfs.

### Why

Up to now Kiro's NVIDIA driver was chosen **at build time** in `kiro-iso-next/build-scripts/build-the-iso.sh` (the `nvidia_driver` variable: `open` / `580xx` / `390xx`) — meaning one ISO per generation. chwd flips that around: one ISO ships with `nvidia-open-dkms` as the sensible default (so the live env boots), and the **installed** system gets the right variant based on what chwd actually detects on the user's hardware. Same ISO serves modern Turing+, legacy Maxwell/Pascal, and old Fermi/Kepler boxes — and laptops with hybrid graphics automatically get `nvidia-prime` + `switcheroo-control` because chwd's `.prime` profile matches DMI chassis types 8/9/10/11.

For non-NVIDIA hardware it's purely additive: chwd installs AMD/Intel-specific bits (currently a no-op since those drivers are in-tree), pulls `broadcom-wl-dkms` if it detects the right Broadcom chipset, and applies handheld-specific tweaks if it's somehow installed on a Steam Deck / ROG Ally / Intel MSI Claw.

### Why keep `kiro_remove_nvidia`

The two modules are complementary, not overlapping:

- `kiro_remove_nvidia` — fast path for `driver=free`: removes the baked-in `nvidia-open-dkms` / `nvidia-utils` / `nvidia-settings` so the user gets a pure nouveau install.
- `chwd` — smart path for `driver=nonfree`: looks at the actual GPU and decides which proprietary variant fits.

A future cleanup could fold both into a single module, but that's a separate refactor — for now keeping them split makes the boundary obvious and means the previously-validated `driver=free` path is untouched.

### chwd source

- Upstream: [github.com/CachyOS/chwd](https://github.com/CachyOS/chwd) — Rust, GPL-3.0
- Profiles: TOML files under `/var/lib/chwd/db/pci/` and `db/usb/`, with NVIDIA device-ID allowlists in `/var/lib/chwd/ids/`
- Installed in the live ISO via `nemesis_repo` (Kiro mirrors the upstream PKGBUILD into our own repo to keep the dependency under our control rather than pinning users to `[cachyos]`)

### Validation pre-merge

Source-reviewed the entire chwd profile catalog (priorities, device_id matching, DMI chassis-type gating) before committing. Compared CachyOS's own integration recipe verbatim against this implementation — same Python jobmodule pattern, same `arch-chroot ... chwd --autoconfigure` invocation, same position relative to `unpackfs`/`initcpiocfg`. Smoke-tested `chwd-arch-git` on the dev host: correct Intel GPU detection, correct profile match.

### Pairs With

- [kiro-iso-next](../kiro-iso-next/) — added `chwd`, `b43-fwcutter`, `broadcom-wl-dkms`, and `hwdetect` to `archiso/packages.x86_64` so the live ISO carries everything the module + its installed-system rerun (`sudo chwd -a`) needs.

**Files modified**
- `usr/lib/calamares/modules/chwd/module.desc` (new)
- `usr/lib/calamares/modules/chwd/main.py` (new)
- `etc/calamares/settings.conf` — `chwd` inserted into exec sequence between `kiro_remove_nvidia` and `initcpiocfg`

---

## 2026-05-28 — install-perf bundle synced from production

All four install-time performance optimisations developed and validated in `kiro-calamares-config` on this same date are now mirrored here. None of these is a beta-only experiment — they all passed a full install + first-boot validation on the production VM before sync.

### Changes synced

**`kiro_before/main.py`** — new `CACHE_TRIGGER_DIRS` tuple + new `snapshot_cache_trigger_mtimes()` step; the old `suppress_mkinitcpio_hook()` is generalised into `suppress_pacman_hooks()` driven by a `SUPPRESSED_HOOKS` tuple covering `90-mkinitcpio-install.hook` plus six heavyweight cache-rebuild hooks (`gtk-update-icon-cache`, `update-desktop-database`, `30-update-mime-database`, `fontconfig`, `dconf-update`, `xorg-mkfontscale`). Each is shadowed to `/dev/null` under `/etc/pacman.d/hooks/` for the duration of the install.

**`kiro_final/main.py`** — mirror `SUPPRESSED_HOOKS` tuple; new `CACHE_REBUILD_STEPS` carrying `(description, shell command, trigger dir)` per cache; new `_cache_trigger_changed()` helper that compares each current trigger-dir mtime against the baseline kiro_before snapshotted pre-install and skips no-op rebuilds; the old single-hook restore is replaced with `restore_suppressed_hooks()` looping over the same tuple; new `rebuild_caches_once()` runs each underlying cache command in the chroot exactly once per install, gated on the mtime check. Without the gate, `update-mime-database` alone cost ~8 s; with the gate, it only runs when something actually changed `/usr/share/mime/packages/`.

**`kiro_ucode/main.py`** — added `_detect_target_virt()` and an early-return at the top of `run()` when `systemd-detect-virt` in the target chroot returns anything other than `none`. Microcode install + wrong-vendor removal is pure waste on a VM (hypervisor handles guest microcode); the VM-skip branch saves ~5 s per VM install. Bare metal is unaffected. Also added an `is_installed_in_target()` guard inside `remove_ucode_package()` so the wrong-vendor `pacman -R` is skipped when nothing's installed (~2-3 s saving when applicable).

### Measured impact

On a VirtualBox install: ~10 s of real work removed (~5 s kiro_ucode VM skip + ~5 s skipped cache rebuilds). Wall-clock didn't visibly drop on a single A/B run because unpackfs/partition variance was on the same order, but across runs the saving is consistent. First-boot freshness is preserved: every cache that could be stale gets rebuilt; only verifiably no-op rebuilds are skipped.

### Beta-specific divergence preserved

`kiro_final` still removes `kiro-calamares-config-next` (not `kiro-calamares-config`) as the installer's self-cleanup step. That one-line difference is the only intentional divergence between this repo and production after the sync.

**Files modified**
- `usr/lib/calamares/modules/kiro_before/main.py`
- `usr/lib/calamares/modules/kiro_final/main.py`
- `usr/lib/calamares/modules/kiro_ucode/main.py`

---

## 2026-05-27 — kiro_final: remove the live-only desktop-launcher trust helper

`kiro_final` now removes **`/usr/local/bin/kiro-trust-desktop-launchers`** from the installed system. That helper is a new live-ISO autostart (added in `kiro-iso-next`) that pre-trusts the **Install kiro** desktop launcher so XFCE/Thunar doesn't prompt — useful only on the live session, so it's added to the `paths_to_remove` list. Its autostart entry under `/home/liveuser/.config/autostart/` needs no explicit cleanup: `removeuser` deletes the live user's home earlier in the sequence, so listing it could even error depending on timing.

## 2026-05-27 — kernel-agnostic installer (new `kiro_kernel` module)

### What Changed

- **New `kiro_kernel` module makes the installer independent of the ISO's kernel package.** Previously three places hardcoded `linux-lqx`: the `unpackfs@vmlinuz` job (copied `vmlinuz-linux-lqx` from the live medium), `kiro_before`'s preset rename (`kiro` → `linux-lqx.preset`), and the static `kiro` preset content. A fork that swapped `linux-lqx` for `linux-zen` (or any kernel) in the ISO would get a broken install. `kiro_kernel` now **detects** the kernel from the live boot medium (`/run/archiso/bootmnt/arch/boot/x86_64/vmlinuz-*`), **copies** the image to `/boot/vmlinuz-<kernel>`, **generates** a matching `/etc/mkinitcpio.d/<kernel>.preset`, and **removes** the live-only preset artifacts (`kiro`, `linux.preset`). Result: changing the ISO's kernel needs **zero edits to the calamares config**.
- **`unpackfs@vmlinuz` removed.** Replaced in the exec sequence by `kiro_kernel` (same slot, right after `unpackfs@rootfs`). The `vmlinuz` unpackfs instance and `unpackfs2.conf` are deleted.
- **`kiro_before` no longer renames the mkinitcpio preset.** `move_mkinitcpio_preset()` and its step are removed; preset handling now lives entirely in `kiro_kernel`.
- **Multi-kernel support.** `kiro_kernel` loops over *every* `vmlinuz-*` on the live medium — copying each image and generating a preset for each — so an ISO that ships several kernels (e.g. the build-side selector picking `linux-zen` + `linux-cachyos`) installs all of them. Presets are removed **before** the per-kernel write loop, so when the plain `linux` kernel is installed its legitimate `linux.preset` is regenerated rather than deleted as the archiso artifact. Stores `kiroKernels` (full list) alongside `kiroKernel` (primary, for back-compat).

### Technical Details

- `initcpio.conf` runs `mkinitcpio -P` (all presets). `kiro_kernel` removes `linux.preset` **before** `initcpio` runs (it was previously removed later in `kiro_final`), so exactly one correct preset is processed and one initramfs (`/boot/initramfs-<kernel>.img`) is built. `kiro_final`'s `linux.preset` removal is left as a guarded no-op for safety.
- The detected kernel name is stored in Calamares globalstorage as `kiroKernel` for downstream use / debugging.
- `bootloader.conf` (`kernelPattern: "^vmlinuz.*"`) and the package-provided `/usr/lib/modules/*` kernel dir already make boot-entry generation kernel-agnostic — no change needed there.
- Developed on branch `feature/kernel-agnostic` (restore point: tag `stable-pre-kernel-agnostic`). **Not yet mirrored to production `kiro-calamares-config`** — pending VM validation. Scope is the installer only; making the *ISO itself* boot a different kernel is a separate `kiro-iso` change (boot entries + airootfs presets).

### Files Modified

- [usr/lib/calamares/modules/kiro_kernel/main.py](usr/lib/calamares/modules/kiro_kernel/main.py) (new)
- [usr/lib/calamares/modules/kiro_kernel/module.desc](usr/lib/calamares/modules/kiro_kernel/module.desc) (new)
- [etc/calamares/settings.conf](etc/calamares/settings.conf)
- [usr/lib/calamares/modules/kiro_before/main.py](usr/lib/calamares/modules/kiro_before/main.py)
- [etc/calamares/modules/unpackfs2.conf](etc/calamares/modules/unpackfs2.conf) (deleted)

## 2026-05-26 — cups printing + logrotate.timer enabled on installed system

### What Changed

- **`services-systemd` now enables `cups.socket`.** Printing was off after a fresh install + reboot. The live ISO enabled CUPS via airootfs symlinks, but those are not carried into the installed system, and the Calamares `services-systemd` unit list (ananicy-cpp, tuned, tuned-ppd, firewalld) never enabled cups. Added a `cups.socket` → `enable` → `mandatory: true` entry. Socket activation only — `cups.service` starts on demand when a client opens the print socket, so there is no always-running daemon. Kept in sync with the production `kiro-calamares-config` fix; paired with `kiro-iso-next` trimming its airootfs cups symlinks to socket-only.
- **`services-systemd` now enables `logrotate.timer`** (`mandatory: false`). Caps unbounded growth of file-based logs (`pacman.log`, Xorg/app logs); journald rotates separately via `SystemMaxUse`. `man-db.timer` reviewed and declined (apropos index only, wakeup churn). Mirrors the production `kiro-calamares-config` change.

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
