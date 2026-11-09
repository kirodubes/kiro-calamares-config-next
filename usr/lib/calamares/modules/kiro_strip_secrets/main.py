#!/usr/bin/env python3
"""Calamares module that blanks password and passphrase values in the preserved install record."""

import json
import os

import libcalamares

RECORD = "var/log/Calamares-install.json"

# Calamares only "obscures" these (byte XOR 0xDF), which reverses in one line, and the file stays
# world-readable on purpose so installs can be verified without sudo. So the values go, the keys stay.
SECRET_WORDS = ("password", "passphrase")


def pretty_name():
    """Name shown in the Calamares progress view."""
    return "Removing passwords from the install record"


def _strip(node):
    count = 0
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, str) and value and any(w in key.lower() for w in SECRET_WORDS):
                node[key] = ""
                count += 1
            else:
                count += _strip(value)
    elif isinstance(node, list):
        for item in node:
            count += _strip(item)
    return count


def run():
    """Blank every non-empty password/passphrase string in the install record."""
    path = os.path.join(libcalamares.globalstorage.value("rootMountPoint"), RECORD)
    if not os.path.isfile(path):
        libcalamares.utils.warning(f"{path} not found; nothing to strip.")
        return None

    # A log file must never fail the install at its last step, so a bad record is logged, not raised.
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        count = _strip(data)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=4, ensure_ascii=False)
            fh.write("\n")
    except (OSError, ValueError) as e:
        libcalamares.utils.warning(f"Could not strip secrets from {path}: {e}")
        return None

    libcalamares.utils.debug(f"Blanked {count} secret value(s) in {path}.")
    return None
