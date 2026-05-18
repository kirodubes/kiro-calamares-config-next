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

def move_mkinitcpio_preset():
    """Move kiro mkinitcpio preset to linux.preset."""
    target_root = libcalamares.globalstorage.value("rootMountPoint")
    src = os.path.join(target_root, "etc/mkinitcpio.d/kiro")
    dst = os.path.join(target_root, "etc/mkinitcpio.d/linux.preset")

    libcalamares.utils.debug("Moving kiro preset to linux.preset in target...")
    try:
        os.replace(src, dst)
    except FileNotFoundError:
        msg = f"Preset file not found in target: {src}"
        libcalamares.utils.warning(msg)
        return ("preset-not-found", msg)
    except Exception as e:
        libcalamares.utils.warning(str(e))
        return (
            "preset-rename-error",
            f"Failed to rename preset in target: <pre>{e}</pre>"
        )
    return None

def run():
    """Execute pre-installation configuration steps in sequence."""
    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("Start kiro_before")
    libcalamares.utils.debug("##############################################\n")

    libcalamares.utils.debug("This module will perform the following operations:")
    libcalamares.utils.debug("  1. Wait for pacman lock to be released")
    libcalamares.utils.debug("  2. Initialize pacman keys and populate keyrings (archlinux, chaotic)")
    libcalamares.utils.debug("  3. Move mkinitcpio kiro preset to linux.preset")
    libcalamares.utils.debug("  4. Optimize makepkg.conf (MAKEFLAGS, PKGEXT, OPTIONS)\n")

    functions = [
        ("Wait for pacman lock", wait_for_pacman_lock),
        ("Initialize pacman keys", initialize_pacman_keys),
        ("Move mkinitcpio preset", move_mkinitcpio_preset),
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
