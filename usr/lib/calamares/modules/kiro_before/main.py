#!/usr/bin/env python3

import os
import time
import shutil
import subprocess
import libcalamares
from libcalamares.utils import check_target_env_call

# === Utility: Wait for pacman lock ===
def wait_for_pacman_lock(max_wait=30):
    lock_path = "/var/lib/pacman/db.lck"
    waited = 0
    while os.path.exists(lock_path):
        libcalamares.utils.debug("Pacman is locked. Waiting 5 seconds...")
        time.sleep(5)
        waited += 5
        if waited >= max_wait:
            libcalamares.utils.debug("Timeout reached. Removing pacman lock manually.")
            try:
                os.remove(lock_path)
            except Exception as e:
                return ("pacman-lock-error", f"Could not remove lock file: {e}")
    return None

# === Optimize makepkg.conf ===
def optimize_makepkg_conf():
    target_root = libcalamares.globalstorage.value("rootMountPoint")
    makepkg_conf_path = os.path.join(target_root, "etc/makepkg.conf")

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

            libcalamares.utils.debug("Disabling debug in OPTIONS")
            subprocess.run([
                "sed", "-i",
                r's|\([^!]\)debug|\1!debug|g',
                makepkg_conf_path
            ], check=True)

        except subprocess.CalledProcessError as e:
            return ("makepkg-optimize-error", f"Failed to update makepkg.conf: {e}")
    else:
        libcalamares.utils.debug("Only one core detected. No changes made.")

    return None

# === Initialize pacman keys ===
def initialize_pacman_keys():
    libcalamares.utils.debug("-> Initializing pacman-key and populating keys...")
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

# === Move mkinitcpio preset ===
def move_mkinitcpio_preset():
    target_root = libcalamares.globalstorage.value("rootMountPoint")
    src = os.path.join(target_root, "etc/mkinitcpio.d/kiro")
    dst = os.path.join(target_root, "etc/mkinitcpio.d/linux.preset")

    libcalamares.utils.debug("-> Moving kiro preset to linux.preset in target...")
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

# === Main run function ===
def run():
    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("Start kiro_before")
    libcalamares.utils.debug("#################################\n")

    for step_func in [
        wait_for_pacman_lock,
        initialize_pacman_keys,
        move_mkinitcpio_preset,
        optimize_makepkg_conf
    ]:
        error = step_func()
        if error:
            return error
    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("End kiro_before")
    libcalamares.utils.debug("#################################\n")
    return None
