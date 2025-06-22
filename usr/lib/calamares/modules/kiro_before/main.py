import os
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
            f"Failed to initialize or populate pacman keys: <pre>{e}</pre>"
        )

    # --- Move preset inside target system ---
    libcalamares.utils.debug("-> Moving arcolinux preset to linux.preset in target...")
    try:
        target_root = libcalamares.globalstorage.value("rootMountPoint")
        src = os.path.join(target_root, "etc/mkinitcpio.d/arcolinux")
        dst = os.path.join(target_root, "etc/mkinitcpio.d/linux.preset")
        os.replace(src, dst)  # force overwrite in target
    except FileNotFoundError:
        msg = f"Preset file not found in target: {src}"
        libcalamares.utils.warning(msg)
        return ("preset-not-found", msg)
    except Exception as e:
        libcalamares.utils.warning(str(e))
        return (
            "preset-rename-error",
            f"Failed to rename preset in target: <pre>{e}</pre>"
        )

    libcalamares.utils.debug("=== End arcolinux-before module ===")
    return None  # Success
