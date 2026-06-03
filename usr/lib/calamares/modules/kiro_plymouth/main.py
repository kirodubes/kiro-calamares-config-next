#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calamares module that adds the `plymouth` hook to the target's
/etc/mkinitcpio.conf so the Kiro boot splash is built into every kernel's
initramfs.

It runs between `initcpiocfg` (which writes the HOOKS line) and `initcpio`
(which runs `mkinitcpio -P` for all presets). `initcpiocfg` recomputes HOOKS
from the partition layout and never adds plymouth, so we insert it here, right
after `udev`, leaving every other hook initcpiocfg decided untouched. The hook
is kernel-agnostic: the single `mkinitcpio -P` that follows embeds the splash
into the initramfs of whatever kernel(s) the user selected.

No-op (and never breaks the build) when plymouth is not installed on the target.
"""

import os
import re

import libcalamares


def plymouth_installed(target_root):
    return os.path.exists(os.path.join(target_root, "usr/bin/plymouth"))


def add_hook(conf_path):
    """Insert `plymouth` after `udev` in the HOOKS line. Idempotent."""
    with open(conf_path) as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if not re.match(r"^\s*HOOKS=", line):
            continue
        if re.search(r"\bplymouth\b", line):
            libcalamares.utils.debug("plymouth hook already present - nothing to do")
            return True
        if not re.search(r"\budev\b", line):
            libcalamares.utils.warning("No 'udev' hook found in HOOKS line; skipping")
            return False
        lines[i] = re.sub(r"\budev\b", "udev plymouth", line, count=1)
        libcalamares.utils.debug(f"Updated HOOKS line: {lines[i].strip()}")
        with open(conf_path, "w") as f:
            f.writelines(lines)
        return True

    libcalamares.utils.warning("No HOOKS= line found in mkinitcpio.conf")
    return False


def run():
    """Add the plymouth hook to the target's mkinitcpio.conf."""
    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("Start kiro_plymouth")
    libcalamares.utils.debug("##############################################\n")

    target_root = libcalamares.globalstorage.value("rootMountPoint")

    if not plymouth_installed(target_root):
        libcalamares.utils.debug("plymouth not installed on target - skipping hook")
        return None

    conf_path = os.path.join(target_root, "etc/mkinitcpio.conf")
    if not os.path.exists(conf_path):
        msg = f"{conf_path} not found"
        libcalamares.utils.warning(msg)
        return ("kiro_plymouth: error", msg)

    if not add_hook(conf_path):
        return ("kiro_plymouth: error", "Failed to add plymouth hook to mkinitcpio.conf")

    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("End kiro_plymouth")
    libcalamares.utils.debug("##############################################\n")
    return None
