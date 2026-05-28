#!/usr/bin/env python3
"""
Calamares module for pre-installation system configuration.
Handles pacman lock management, key initialization, mkinitcpio preset migration, and makepkg optimization.
"""

import os
import time
import subprocess
import libcalamares
from libcalamares.utils import check_target_env_call


def wait_for_pacman_lock(max_wait=30):
    """Wait for pacman lock to be released, force remove if timeout exceeded."""
    lock_path = "/var/lib/pacman/db.lck"
    waited = 0

    while os.path.exists(lock_path):
        libcalamares.utils.debug("Pacman is locked. Waiting 5 seconds...")
        time.sleep(5)
        waited += 5
        if waited >= max_wait:
            libcalamares.utils.debug(f"Pacman lock timeout after {max_wait}s. Forcing removal.")
            try:
                os.remove(lock_path)
            except Exception as e:
                return ("pacman-lock-error", f"Could not remove lock file: {e}")
    return None

def optimize_makepkg_conf():
    """Optimize makepkg.conf for system configuration (MAKEFLAGS, PKGEXT, OPTIONS)."""
    target_root = libcalamares.globalstorage.value("rootMountPoint")
    makepkg_conf_path = os.path.join(target_root, "etc/makepkg.conf")
    libcalamares.utils.debug("Optimizing makepkg.conf")

    try:
        cores = os.cpu_count()
        libcalamares.utils.debug(f"Detected {cores} cores on the system.")
    except Exception as e:
        libcalamares.utils.warning(f"Failed to detect number of cores: {e}")
        return ("cpu-detect-failed", f"Could not detect number of CPU cores: {e}")

    if cores and cores > 1:
        try:
            libcalamares.utils.debug(f"Setting MAKEFLAGS to -j{cores}")
            subprocess.run([
                "sed", "-i",
                f's|#MAKEFLAGS="-j2"|MAKEFLAGS="-j{cores}"|g',
                makepkg_conf_path
            ], check=True)

            libcalamares.utils.debug("Changing PKGEXT to .pkg.tar.zst")
            subprocess.run([
                "sed", "-i",
                "s|PKGEXT='.pkg.tar.xz'|PKGEXT='.pkg.tar.zst'|g",
                makepkg_conf_path
            ], check=True)

            libcalamares.utils.debug("Disabling debug in OPTIONS (only in OPTIONS line)")
            # FIXED: Only modify the OPTIONS line, not the entire file
            subprocess.run([
                "sed", "-i",
                '/^OPTIONS=/s/\\bdebug\\b/!debug/',
                makepkg_conf_path
            ], check=True)

        except subprocess.CalledProcessError as e:
            return ("makepkg-optimize-error", f"Failed to update makepkg.conf: {e}")
    else:
        libcalamares.utils.debug("Only one core detected. No changes made.")

    return None

def sync_pacman_databases():
    """Refresh pacman sync databases inside the target chroot.

    Without this, the ISO's pre-bundled /var/lib/pacman/sync/ may be empty
    or stale, and every later chroot `pacman -R`/`-Q` call in kiro_*
    modules emits warnings like:
        warning: database file for 'core' does not exist (use '-Sy')
    """
    # Calamares' welcome module probes connectivity and sets "hasInternet"
    # in globalstorage. Explicit False = offline, so skip cleanly instead
    # of waiting on a pacman timeout. None/unset = unknown, attempt anyway.
    if libcalamares.globalstorage.value("hasInternet") is False:
        libcalamares.utils.debug("hasInternet=False — skipping pacman -Sy")
        return None

    libcalamares.utils.debug("Refreshing pacman sync databases in target chroot")
    try:
        check_target_env_call(["pacman", "-Sy", "--noconfirm"])
    except Exception as e:
        # Best-effort: a flaky mirror or transient DNS hiccup should not
        # abort the install — the rest of the pipeline still works
        # (just with warnings), as it did before this step existed.
        libcalamares.utils.warning(f"pacman -Sy failed (continuing): {e}")
    return None


# Cache trigger directories whose mtime is sampled here so kiro_final can skip
# cache rebuilds whose source data wasn't touched during install. Must mirror
# the trigger paths in kiro_final.CACHE_REBUILD_STEPS.
CACHE_TRIGGER_DIRS = (
    "usr/share/icons",            # gtk-update-icon-cache
    "usr/share/applications",     # update-desktop-database
    "usr/share/mime/packages",    # update-mime-database
    "usr/share/fonts",            # fontconfig + xorg-mkfontscale
    "etc/dconf/db",               # dconf update
)


# Pacman hooks shadowed to /dev/null in the target chroot during install so
# heavyweight cache rebuilds don't fire once per pacman transaction. Each
# transaction (kiro_remove_nvidia, packages, kiro_ucode, kiro_final removals)
# otherwise re-runs the same expensive rebuild from scratch.
#
# kiro_final unlinks every entry below at the very end of the install and runs
# the corresponding underlying command exactly ONCE so the installed system
# boots with correct caches. MUST stay in sync with kiro_final.SUPPRESSED_HOOKS.
SUPPRESSED_HOOKS = (
    "90-mkinitcpio-install.hook",     # initramfs rebuild — explicit Calamares initcpio job is source of truth
    "gtk-update-icon-cache.hook",     # icon theme caches
    "update-desktop-database.hook",   # .desktop MIME cache
    "30-update-mime-database.hook",   # shared MIME database
    "fontconfig.hook",                # fc-cache
    "dconf-update.hook",              # system dconf databases
    "xorg-mkfontscale.hook",          # X font dir indices
)


def snapshot_cache_trigger_mtimes():
    """Snapshot mtimes of every cache trigger dir into globalstorage.

    kiro_final compares these against the post-install mtimes and skips
    cache rebuilds whose trigger dir was untouched during the install. The
    snapshot must happen BEFORE any pacman operation in the install pipeline
    so we capture the pristine post-unpackfs state.
    """
    target_root = libcalamares.globalstorage.value("rootMountPoint")
    snapshot = {}
    for rel in CACHE_TRIGGER_DIRS:
        full = os.path.join(target_root, rel)
        try:
            snapshot[rel] = os.stat(full).st_mtime if os.path.exists(full) else None
        except Exception as e:
            libcalamares.utils.warning(f"Could not stat {full} for cache baseline: {e}")
            snapshot[rel] = None
    libcalamares.globalstorage.insert("kiroCacheMtimeBaseline", snapshot)
    libcalamares.utils.debug(f"Cache trigger mtime baseline: {snapshot}")
    return None


def suppress_pacman_hooks():
    """Symlink heavyweight pacman cache-rebuild hooks to /dev/null in the chroot.

    Pacman searches /etc/pacman.d/hooks/ before /usr/share/libalpm/hooks/, so a
    same-name /dev/null symlink in the former shadows the upstream hook for
    every pacman transaction during the install. The 90-mkinitcpio-install
    suppression has been in place since 2026-05-28 and saved ~30-60s by
    eliminating 5 throwaway initramfs rebuilds during a 2-kernel install. The
    same anti-pattern applies to icon/desktop/MIME/font/dconf hooks — each
    fires per transaction and rebuilds the same caches every time.

    kiro_final MUST restore these symlinks at the end and run each underlying
    rebuild once — leaving a /dev/null symlink behind would prevent the user's
    first `pacman -Syu` from refreshing the relevant cache, leading to stale
    icons/fonts/MIME types/initramfs after future upgrades.
    """
    target_root = libcalamares.globalstorage.value("rootMountPoint")
    hooks_dir = os.path.join(target_root, "etc/pacman.d/hooks")

    try:
        os.makedirs(hooks_dir, exist_ok=True)
    except Exception as e:
        libcalamares.utils.warning(f"Could not create hooks dir (continuing): {e}")
        return None

    for hook in SUPPRESSED_HOOKS:
        path = os.path.join(hooks_dir, hook)
        try:
            # Idempotent: drop any existing override so re-runs don't ENOENT.
            if os.path.lexists(path):
                os.unlink(path)
            os.symlink("/dev/null", path)
            libcalamares.utils.debug(f"Suppressed pacman hook: {path} -> /dev/null")
        except Exception as e:
            # Best-effort optimisation — a failure on one hook only loses that
            # hook's speed-up, it does not break the install.
            libcalamares.utils.warning(f"Could not suppress {hook} (continuing): {e}")
    return None


def initialize_pacman_keys():
    """Initialize pacman keys and populate keyrings (archlinux, chaotic)."""
    target_root = libcalamares.globalstorage.value("rootMountPoint")
    keyring_path = os.path.join(target_root, "etc/pacman.d/gnupg/pubring.gpg")

    # Skip if keyring already exists (ISO has pre-initialized keys)
    if os.path.exists(keyring_path):
        libcalamares.utils.debug("Pacman keyring already initialized. Skipping.")
        return None

    libcalamares.utils.debug("Initializing pacman-key and populating keys...")
    try:
        check_target_env_call(["pacman-key", "--init"])
        check_target_env_call(["pacman-key", "--populate", "archlinux"])
        check_target_env_call(["pacman-key", "--populate", "chaotic"])
    except Exception as e:
        libcalamares.utils.warning(str(e))
        return (
            "pacman-key-error",
            f"Failed to initialize or populate pacman keys: <pre>{e}</pre>"
        )
    return None

def run():
    """Execute pre-installation configuration steps in sequence."""
    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("Start kiro_before")
    libcalamares.utils.debug("##############################################\n")

    libcalamares.utils.debug("This module will perform the following operations:")
    libcalamares.utils.debug("  1. Wait for pacman lock to be released")
    libcalamares.utils.debug("  2. Snapshot cache trigger dir mtimes (perf — paired with kiro_final)")
    libcalamares.utils.debug("  3. Suppress heavyweight pacman hooks (perf — restored in kiro_final)")
    libcalamares.utils.debug("  4. Initialize pacman keys and populate keyrings (archlinux, chaotic)")
    libcalamares.utils.debug("  5. Refresh pacman sync databases (pacman -Sy)")
    libcalamares.utils.debug("  6. Optimize makepkg.conf (MAKEFLAGS, PKGEXT, OPTIONS)\n")

    functions = [
        ("Wait for pacman lock", wait_for_pacman_lock),
        ("Snapshot cache mtimes", snapshot_cache_trigger_mtimes),
        ("Suppress pacman hooks", suppress_pacman_hooks),
        ("Initialize pacman keys", initialize_pacman_keys),
        ("Sync pacman databases", sync_pacman_databases),
        ("Optimize makepkg.conf", optimize_makepkg_conf)
    ]

    results = {}
    for func_name, step_func in functions:
        error = step_func()
        if error:
            results[func_name] = "FAILED"
            return error
        results[func_name] = "SUCCESS"

    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("End kiro_before - Function Results:")
    for func_name, status in results.items():
        libcalamares.utils.debug(f"  {func_name}: {status}")
    libcalamares.utils.debug("##############################################\n")
    return None
