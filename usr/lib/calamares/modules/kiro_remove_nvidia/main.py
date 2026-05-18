#!/usr/bin/env python3
"""
Calamares module for conditional NVIDIA driver removal.
Removes NVIDIA packages based on kernel cmdline 'driver' parameter.
"""

import os
import time
import subprocess
import libcalamares
from libcalamares.utils import check_target_env_call


def kernel_cmdline(param_name, default=None):
    """Parse /proc/cmdline for a parameter value."""
    try:
        with open("/proc/cmdline", "r") as f:
            params = f.read().strip().split()
        for param in params:
            if param.startswith(param_name + "="):
                return param.split("=", 1)[1]
            elif param == param_name:
                return ""
    except Exception as e:
        libcalamares.utils.debug(f"Error reading /proc/cmdline: {e}")
    return default

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

def _is_installed_in_target(pkg: str) -> bool:
    """
    Returns True if pkg is installed in the target environment.
    Uses: pacman -Q <pkg> (exit 0 if installed, non-zero if not).
    """
    try:
        check_target_env_call(["pacman", "-Q", pkg])
        return True
    except subprocess.CalledProcessError:
        return False

def remove_nvidia_packages_from_target():
    """Remove NVIDIA-related packages from the target system (only if installed)."""
    candidates = ["nvidia-open-dkms", "nvidia-utils", "nvidia-settings"]

    # Only remove packages that are actually installed in the target.
    installed = [p for p in candidates if _is_installed_in_target(p)]

    if not installed:
        libcalamares.utils.debug("No NVIDIA packages installed in target; skipping removal.")
        return None  # Continue Calamares normally.

    try:
        check_target_env_call(["pacman", "-Rns", "--noconfirm"] + installed)
    except subprocess.CalledProcessError as e:
        # At this point something *real* failed (deps, locks, etc.)
        libcalamares.utils.warning(str(e))
        return ("nvidia-remove-failed", f"Failed to remove NVIDIA packages: <pre>{e}</pre>")

    return None

def run():
    """Execute NVIDIA package removal based on kernel cmdline parameter."""
    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("Start kiro_remove_nvidia")
    libcalamares.utils.debug("##############################################\n")

    libcalamares.utils.debug("This module will perform the following operations:")
    libcalamares.utils.debug("  1. Read kernel cmdline 'driver' parameter")
    libcalamares.utils.debug("  2. Wait for pacman lock to be released")
    libcalamares.utils.debug("  3. Remove NVIDIA packages if driver=free is set\n")

    results = {}

    selection = kernel_cmdline("driver", default="free")
    libcalamares.utils.debug(f"Kernel parameter 'driver' = {selection}")

    # Wait for pacman lock
    error = wait_for_pacman_lock()
    if error:
        results["Wait for pacman lock"] = "FAILED"
        return error
    results["Wait for pacman lock"] = "SUCCESS"

    if selection == "free":
        libcalamares.utils.debug("Removing NVIDIA packages because 'driver=free' was specified.")
        error = remove_nvidia_packages_from_target()
        if error:
            results["Remove NVIDIA packages"] = "FAILED"
            return error
        results["Remove NVIDIA packages"] = "SUCCESS"
    else:
        libcalamares.utils.debug("Skipping NVIDIA removal because 'driver=free' not set.")
        results["Remove NVIDIA packages"] = "SKIPPED"

    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("End kiro_remove_nvidia - Function Results:")
    for func_name, status in results.items():
        libcalamares.utils.debug(f"  {func_name}: {status}")
    libcalamares.utils.debug("##############################################\n")

    return None
