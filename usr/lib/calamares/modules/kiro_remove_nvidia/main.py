#!/usr/bin/env python3

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

def remove_nvidia_packages_from_target():
    """Remove NVIDIA-related packages from the target system."""
    packages = ["nvidia-dkms", "nvidia-utils", "nvidia-settings"]
    try:
        check_target_env_call(["pacman", "-Rns", "--noconfirm"] + packages)
    except subprocess.CalledProcessError as e:
        libcalamares.utils.warning(str(e))
        return ("nvidia-remove-failed", f"Failed to remove NVIDIA packages: <pre>{e}</pre>")
    return None

def run():
    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("Start kiro_remove_nvidia")
    libcalamares.utils.debug("#################################\n")

    selection = kernel_cmdline("driver", default="free")
    libcalamares.utils.debug(f"Kernel parameter 'driver' = {selection}")

    # Wait for pacman lock
    error = wait_for_pacman_lock()
    if error:
        return error

    if selection == "free":
        libcalamares.utils.debug("Removing NVIDIA packages because 'driver=free' was specified.")
        error = remove_nvidia_packages_from_target()
        if error:
            return error
    else:
        libcalamares.utils.debug("Skipping NVIDIA removal because 'driver=free' not set.")

    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("End kiro_remove_nvidia")
    libcalamares.utils.debug("#################################\n")

    return None
