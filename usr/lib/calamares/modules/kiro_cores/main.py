#!/usr/bin/env python3

import os
import time
import subprocess
import libcalamares
from libcalamares.utils import check_target_env_call

def wait_for_pacman_lock(max_wait=30):
    """Wait for pacman lock to disappear, max 30 seconds."""
    waited = 0
    lock_path = "/var/lib/pacman/db.lck"
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

def optimize_makepkg_conf():
    """Optimize makepkg.conf in the target system based on number of CPU cores."""
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
            # Set MAKEFLAGS
            libcalamares.utils.debug(f"Setting MAKEFLAGS to -j{cores}")
            subprocess.run([
                "sed", "-i",
                f's|#MAKEFLAGS="-j2"|MAKEFLAGS="-j{cores}"|g',
                makepkg_conf_path
            ], check=True)

            # Set PKGEXT
            libcalamares.utils.debug("Changing PKGEXT to .pkg.tar.zst")
            subprocess.run([
                "sed", "-i",
                "s|PKGEXT='.pkg.tar.xz'|PKGEXT='.pkg.tar.zst'|g",
                makepkg_conf_path
            ], check=True)

            # Change debug to !debug in OPTIONS
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

def run():
    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("Start arcolinux-optimize-makepkg")
    libcalamares.utils.debug("#################################\n")

    error = wait_for_pacman_lock()
    if error:
        return error

    error = optimize_makepkg_conf()
    if error:
        return error

    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("End arcolinux-optimize-makepkg")
    libcalamares.utils.debug("#################################\n")

    return None
