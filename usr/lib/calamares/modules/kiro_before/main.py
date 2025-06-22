#!/usr/bin/env python3

import shutil
import libcalamares
from libcalamares.utils import check_target_env_call

def run():
    libcalamares.utils.debug("=== Start arcolinux-before module ===")

    # --- Populate pacman keys ---
    libcalamares.utils.debug("-> Initializing pacman-key and populating keys...")
    try:
        check_target_env_call(["pacman-key", "--init"])
        check_target_env_call(["pacman-key", "--populate", "archlinux"])
        check_target_env_call(["pacman-key", "--populate", "chaotic"])
    except Exception as e:
        libcalamares.utils.warning(str(e))
        return (
            "pacman-key-error",
            "Failed to initialize or populate pacman keys: <pre>{}</pre>".format(e)
        )

    # --- Move arcolinux preset ---
    libcalamares.utils.debug("-> Moving /etc/mkinitcpio.d/arcolinux to linux.preset...")
    try:
        shutil.move("/etc/mkinitcpio.d/arcolinux", "/etc/mkinitcpio.d/linux.preset")
    except FileNotFoundError:
        msg = "Preset file not found: /etc/mkinitcpio.d/arcolinux"
        libcalamares.utils.warning(msg)
        return ("preset-not-found", msg)
    except Exception as e:
        libcalamares.utils.warning(str(e))
        return (
            "preset-rename-error",
            "Failed to rename preset: <pre>{}</pre>".format(e)
        )

    libcalamares.utils.debug("=== End arcolinux-before module ===")
    return None  # Success
