#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calamares module that makes the target's /etc/mkinitcpio.conf Plymouth-aware so the
Kiro boot splash is built into every kernel's initramfs.

It runs between `initcpiocfg` (which writes the HOOKS line) and `initcpio`
(which runs `mkinitcpio -P` for all presets). `initcpiocfg` recomputes HOOKS
from the partition layout and never adds plymouth, so we insert `plymouth` here, right
after `udev`, leaving every other hook initcpiocfg decided untouched. On an *encrypted*
install we also swap the plain `encrypt` hook for `plymouth-encrypt`, so the LUKS
passphrase prompt is drawn through the splash instead of being hidden behind it (with
plain `encrypt` the prompt is invisible and boot stalls). Both edits are kernel-agnostic:
the single `mkinitcpio -P` that follows embeds the result into every selected kernel.

No-op (and never breaks the build) when plymouth is not installed on the target.
"""

import os
import re

import libcalamares


def plymouth_installed(target_root):
    return os.path.exists(os.path.join(target_root, "usr/bin/plymouth"))


def add_hook(conf_path):
    """Make the target's HOOKS line Plymouth-aware. Two idempotent edits:

    1. insert `plymouth` after `udev` so the splash is built into the initramfs;
    2. on an encrypted install, swap the plain `encrypt` hook for `plymouth-encrypt`
       so the LUKS passphrase prompt renders *through* the splash. With plain `encrypt`
       the prompt is drawn on the console *underneath* the already-running splash, so it
       is invisible and boot stalls waiting for input the user can't see.
    """
    with open(conf_path) as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if not re.match(r"^\s*HOOKS=", line):
            continue

        new = line
        # 1. plymouth after udev (skip if already present)
        if not re.search(r"\bplymouth\b", new):
            if not re.search(r"\budev\b", new):
                libcalamares.utils.warning("No 'udev' hook found in HOOKS line; skipping")
                return False
            new = re.sub(r"\budev\b", "udev plymouth", new, count=1)
        # 2. encrypt -> plymouth-encrypt; standalone token only, so an already-converted
        #    plymouth-encrypt (and sd-encrypt) are left untouched -> idempotent.
        new = re.sub(r"(?<![\w-])encrypt(?![\w-])", "plymouth-encrypt", new)

        if new != line:
            lines[i] = new
            with open(conf_path, "w") as f:
                f.writelines(lines)
            libcalamares.utils.debug(f"Updated HOOKS line: {new.strip()}")
        else:
            libcalamares.utils.debug("HOOKS already Plymouth-aware - nothing to do")
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
