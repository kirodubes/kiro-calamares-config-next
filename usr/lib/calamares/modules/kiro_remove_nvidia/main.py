#!/usr/bin/env python3
"""
Calamares module for conditional NVIDIA driver removal.
Removes NVIDIA packages based on kernel cmdline 'driver' parameter.
"""

import os
import time
import subprocess
import libcalamares
from libcalamares.utils import check_target_env_call, check_target_env_output


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

def nvidia_stack_from_names(names):
    """The NVIDIA driver packages among a list of real installed package names.

    Variant-agnostic: matches nvidia-open-dkms, nvidia-utils, nvidia-settings AND
    the nvidia-390xx-* / nvidia-580xx-* variants, by REAL installed name. This is
    the fix for the old hardcoded ["nvidia-open-dkms","nvidia-utils","nvidia-settings"]
    list: `pacman -Q nvidia-utils` resolves the provide (nvidia-390xx-utils), so the
    old code thought it was installed, but `pacman -Rns nvidia-utils` does NOT resolve
    provides → "target not found" → install aborted on 390xx/580xx ISOs.
    """
    return [n for n in names
            if n.startswith("nvidia-") and n.rsplit("-", 1)[-1] in ("dkms", "utils", "settings")]

def installed_nvidia_stack():
    """The NVIDIA driver packages actually installed in the target (real names)."""
    try:
        out = check_target_env_output(["pacman", "-Qq"])
    except subprocess.CalledProcessError:
        return []
    return nvidia_stack_from_names(out.split())

def remove_nvidia_packages_from_target():
    """Remove the installed NVIDIA driver stack from the target (any variant)."""
    pkgs = installed_nvidia_stack()

    if not pkgs:
        libcalamares.utils.debug("No NVIDIA packages installed in target; skipping removal.")
        return None  # Continue Calamares normally.

    libcalamares.utils.debug(f"Removing NVIDIA packages: {' '.join(pkgs)}")
    try:
        # Remove dkms + utils + settings together so there's no dependency-order
        # failure (the dkms driver depends on its -utils).
        check_target_env_call(["pacman", "-Rns", "--noconfirm"] + pkgs)
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
    libcalamares.utils.debug("  3. Remove NVIDIA packages if driver=free or driver=nonfreechwd\n")

    results = {}

    selection = kernel_cmdline("driver", default="free")
    libcalamares.utils.debug(f"Kernel parameter 'driver' = {selection}")

    # Wait for pacman lock
    error = wait_for_pacman_lock()
    if error:
        results["Wait for pacman lock"] = "FAILED"
        return error
    results["Wait for pacman lock"] = "SUCCESS"

    # Remove on 'free' (end up on mesa) and on 'nonfreechwd' (clean slate so chwd
    # installs exactly its detected pick with nothing to conflict). Plain 'nonfree'
    # keeps the baked nvidia-open-dkms untouched.
    if selection in ("free", "nonfreechwd"):
        libcalamares.utils.debug(f"Removing NVIDIA packages because 'driver={selection}' was specified.")
        error = remove_nvidia_packages_from_target()
        if error:
            results["Remove NVIDIA packages"] = "FAILED"
            return error
        results["Remove NVIDIA packages"] = "SUCCESS"
    else:
        libcalamares.utils.debug(f"Keeping NVIDIA packages because 'driver={selection}' (baked nvidia-open-dkms).")
        results["Remove NVIDIA packages"] = "SKIPPED"

    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("End kiro_remove_nvidia - Function Results:")
    for func_name, status in results.items():
        libcalamares.utils.debug(f"  {func_name}: {status}")
    libcalamares.utils.debug("##############################################\n")

    return None
