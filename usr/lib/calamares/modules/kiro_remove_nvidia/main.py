#!/usr/bin/env python3

import os
import time
import subprocess
import libcalamares

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
    while os.path.exists("/var/lib/pacman/db.lck"):
        libcalamares.utils.debug("Pacman is not ready yet. Waiting 5 seconds...")
        time.sleep(5)
        waited += 5
        if waited >= max_wait:
            libcalamares.utils.debug("Warning: removing pacman db.lck after 30 seconds wait.")
            try:
                os.remove("/var/lib/pacman/db.lck")
            except Exception as e:
                return ("pacman-lock-error", f"Could not remove lock file: {e}")
    return None

def remove_nvidia_packages():
    packages = ["nvidia-dkms", "nvidia-utils", "nvidia-settings", "egl-wayland"]
    try:
        subprocess.run(["pacman", "-Rns", "--noconfirm"] + packages, check=True)
    except subprocess.CalledProcessError as e:
        return ("nvidia-remove-failed", f"Failed to remove NVIDIA packages: {e}")
    return None

def run():
    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("Start arcolinux-remove-nvidia")
    libcalamares.utils.debug("#################################\n")

    selection = kernel_cmdline("driver", default="free")
    libcalamares.utils.debug(f"Selection was {selection}")

    # Wait for pacman lock
    error = wait_for_pacman_lock()
    if error:
        return error

    if selection == "free":
        libcalamares.utils.debug("Removing all NVIDIA-related packages (driver=free).")
        error = remove_nvidia_packages()
        if error:
            return error

    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("End arcolinux-remove-nvidia")
    libcalamares.utils.debug("#################################\n")

    return None
