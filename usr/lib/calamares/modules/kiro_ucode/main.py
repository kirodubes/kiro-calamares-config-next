#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calamares module for CPU microcode package installation.
Detects CPU vendor and installs appropriate microcode package from /etc/calamares/packages.
"""

import libcalamares
import subprocess
import os
import glob
from libcalamares.utils import target_env_call


class ConfigController:
    """Controller for CPU microcode configuration."""

    def __init__(self):
        """Initialize with target root mount point."""
        self.__root = libcalamares.globalstorage.value("rootMountPoint")

    @property
    def root(self):
        """Get the target root mount point."""
        return self.__root

    def detect_cpu_vendor(self):
        """Detect CPU vendor (AuthenticAMD or GenuineIntel)."""
        try:
            vendor = subprocess.getoutput(
                "hwinfo --cpu | grep Vendor: -m1 | cut -d'\"' -f2"
            ).strip()
            libcalamares.utils.debug(f"Detected CPU vendor: {vendor}")
            return vendor
        except Exception as e:
            libcalamares.utils.warning(f"Failed to detect CPU vendor: {e}")
            return None

    def find_package_file(self, package_name):
        """Find package file in /etc/calamares/packages directory on live DVD."""
        packages_dir = "/etc/calamares/packages"
        pattern = os.path.join(packages_dir, f"{package_name}-*.pkg.tar.zst")

        files = glob.glob(pattern)
        if files:
            return files[0]
        return None

    def install_ucode_package(self, package_name):
        """Install microcode package from /etc/calamares/packages on live DVD."""
        package_file = self.find_package_file(package_name)

        if not package_file:
            libcalamares.utils.warning(f"Package file not found for {package_name}")
            return False

        libcalamares.utils.debug(f"Installing {package_name} from {package_file}")
        try:
            target_env_call(["pacman", "-U", package_file, "--noconfirm"])
            libcalamares.utils.debug(f"Successfully installed {package_name}")
            return True
        except Exception as e:
            libcalamares.utils.warning(f"Failed to install {package_name}: {e}")
            return False

    def handle_ucode(self):
        """Install appropriate microcode package based on detected CPU vendor."""
        vendor = self.detect_cpu_vendor()

        if vendor == "AuthenticAMD":
            libcalamares.utils.debug("Installing amd-ucode for AMD CPU.")
            self.install_ucode_package("amd-ucode")
        elif vendor == "GenuineIntel":
            libcalamares.utils.debug("Installing intel-ucode for Intel CPU.")
            self.install_ucode_package("intel-ucode")
        else:
            libcalamares.utils.debug("Unknown CPU vendor or detection failed. Skipping microcode installation.")

    def run(self):
        """Execute microcode configuration."""
        self.handle_ucode()
        return None


def run():
    """Execute CPU microcode configuration."""
    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("Start kiro_ucode")
    libcalamares.utils.debug("##############################################\n")

    libcalamares.utils.debug("This module will perform the following operations:")
    libcalamares.utils.debug("  1. Detect CPU vendor (AuthenticAMD or GenuineIntel)")
    libcalamares.utils.debug("  2. Install appropriate microcode package from /etc/calamares/packages\n")

    results = {}
    config = ConfigController()
    result = config.run()

    results["Handle microcode"] = "SUCCESS" if result is None else "FAILED"

    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("End kiro_ucode - Function Results:")
    for func_name, status in results.items():
        libcalamares.utils.debug(f"  {func_name}: {status}")
    libcalamares.utils.debug("##############################################\n")

    return result
