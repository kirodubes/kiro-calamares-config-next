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


def suppress_mkinitcpio_hook():
    """Symlink the upstream mkinitcpio pacman hook to /dev/null in the chroot so
    package operations during install don't trigger redundant initramfs rebuilds.

    Calamares' own `initcpiocfg` + `Creating initramfs with mkinitcpio…` job runs
    `mkinitcpio -P` explicitly with the final mkinitcpio.conf — that's the source
    of truth. Every other rebuild during install (nvidia-* removal via DKMS,
    `mkinitcpio-archiso` removal in the packages module, `kiro_ucode` microcode
    swap, kiro_final VM cleanup) is throwaway work: same kernels, same config,
    each pass building the same N images. Observed 2026-05-28: 5 hook-triggered
    rebuilds during a 2-kernel install (10 image builds total), ~30-60s of churn.

    Suppressing the install hook eliminates those passes; the explicit Calamares
    mkinitcpio job still runs because it invokes mkinitcpio directly, not via
    the hook. kiro_final reverses this symlink at the very end of the install so
    the user's first `pacman -Syu` rebuilds initramfs normally on kernel
    upgrades — the override MUST be removed there, otherwise a stuck /dev/null
    symlink leaves the user's system unable to refresh initramfs after a kernel
    package change.
    """
    target_root = libcalamares.globalstorage.value("rootMountPoint")
    hooks_dir = os.path.join(target_root, "etc/pacman.d/hooks")
    hook_override = os.path.join(hooks_dir, "90-mkinitcpio-install.hook")

    try:
        os.makedirs(hooks_dir, exist_ok=True)
        # Idempotent: drop any existing override so re-runs don't ENOENT.
        if os.path.lexists(hook_override):
            os.unlink(hook_override)
        os.symlink("/dev/null", hook_override)
        libcalamares.utils.debug(
            f"Suppressed upstream mkinitcpio pacman hook: {hook_override} -> /dev/null"
        )
    except Exception as e:
        # Best-effort optimisation — a failure here only loses the speed-up,
        # it does not break the install.
        libcalamares.utils.warning(f"Could not suppress mkinitcpio hook (continuing): {e}")
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
    libcalamares.utils.debug("  2. Suppress mkinitcpio pacman hook (perf — restored in kiro_final)")
    libcalamares.utils.debug("  3. Initialize pacman keys and populate keyrings (archlinux, chaotic)")
    libcalamares.utils.debug("  4. Refresh pacman sync databases (pacman -Sy)")
    libcalamares.utils.debug("  5. Optimize makepkg.conf (MAKEFLAGS, PKGEXT, OPTIONS)\n")

    functions = [
        ("Wait for pacman lock", wait_for_pacman_lock),
        ("Suppress mkinitcpio hook", suppress_mkinitcpio_hook),
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
