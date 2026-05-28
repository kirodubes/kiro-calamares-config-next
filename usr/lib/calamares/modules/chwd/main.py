#!/usr/bin/env python3
"""
Calamares module for hardware-aware driver installation via chwd.

Runs `chwd --autoconfigure` inside the chroot to install the optimal driver
profile for the detected hardware (GPU, network adapter, microcode-aware
laptop tweaks, hybrid graphics, etc.).

Honours the GRUB-menu `driver=` kernel cmdline:
  - driver=free    -> skip chwd entirely; kiro_remove_nvidia already cleaned
                     up proprietary NVIDIA, leave nouveau in place.
  - driver=nonfree -> run chwd; let it pick the right NVIDIA / AMD / Intel
                     profile from the detected device IDs.
"""

import os
import subprocess
import time

import libcalamares


status_update_time = 0


def pretty_name():
    return "Installing hardware drivers via chwd..."


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


def line_cb(line):
    """Pipe chwd output into the Calamares debug log + tick progress."""
    global status_update_time
    libcalamares.utils.debug("chwd: " + line.strip())
    if (time.time() - status_update_time) > 0.5:
        libcalamares.job.setprogress(0)
        status_update_time = time.time()


def run_in_host(command, line_func):
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1,
    )
    for line in proc.stdout:
        if line.strip():
            line_func(line)
    proc.wait()
    if proc.returncode != 0:
        return ("chwd-failed", f"chwd exited with code {proc.returncode}")
    return None


def run():
    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("Start chwd")
    libcalamares.utils.debug("##############################################\n")

    selection = kernel_cmdline("driver", default="free")
    libcalamares.utils.debug(f"Kernel parameter 'driver' = {selection}")

    if selection == "free":
        libcalamares.utils.debug(
            "Skipping chwd because 'driver=free' was specified — "
            "kiro_remove_nvidia already cleaned up proprietary drivers."
        )
        return None

    root_mount_point = libcalamares.globalstorage.value("rootMountPoint")
    if not root_mount_point:
        return (
            "No mount point for root partition",
            "globalstorage does not contain a 'rootMountPoint' key.",
        )
    if not os.path.exists(root_mount_point):
        return (
            "Bad mount point for root partition",
            f"'{root_mount_point}' does not exist.",
        )

    chwd_command = ["arch-chroot", root_mount_point, "chwd", "--autoconfigure"]
    libcalamares.utils.debug(f"Running: {' '.join(chwd_command)}")

    error = run_in_host(chwd_command, line_cb)
    if error:
        return error

    libcalamares.job.setprogress(1.0)

    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("End chwd")
    libcalamares.utils.debug("##############################################\n")

    return None
