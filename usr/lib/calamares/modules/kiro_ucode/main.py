#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# === This file is part of Calamares - <http://github.com/calamares> ===
#

import libcalamares
import subprocess
from libcalamares.utils import target_env_call


class ConfigController:
    def __init__(self):
        self.__root = libcalamares.globalstorage.value("rootMountPoint")

    @property
    def root(self):
        return self.__root

    def detect_cpu_vendor(self):
        try:
            vendor = subprocess.getoutput(
                "hwinfo --cpu | grep Vendor: -m1 | cut -d'\"' -f2"
            ).strip()
            libcalamares.utils.debug(f"Detected CPU vendor: {vendor}")
            return vendor
        except Exception as e:
            libcalamares.utils.warning(f"Failed to detect CPU vendor: {e}")
            return None

    def handle_ucode(self):
        vendor = self.detect_cpu_vendor()
        if vendor == "AuthenticAMD":
            libcalamares.utils.debug("Removing intel-ucode for AMD CPU.")
            target_env_call(["pacman", "-R", "intel-ucode", "--noconfirm"])
        elif vendor == "GenuineIntel":
            libcalamares.utils.debug("Removing amd-ucode for Intel CPU.")
            target_env_call(["pacman", "-R", "amd-ucode", "--noconfirm"])
        else:
            libcalamares.utils.debug("Unknown CPU vendor or detection failed.")
        
        libcalamares.utils.debug("#################################")
        libcalamares.utils.debug("End kiro_ucode")
        libcalamares.utils.debug("#################################\n")

    def run(self):
        self.handle_ucode()
        return None


def run():
    """Post-install configuration tasks."""
    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("Start kiro_ucode")
    libcalamares.utils.debug("#################################\n")
    config = ConfigController()
    return config.run()
