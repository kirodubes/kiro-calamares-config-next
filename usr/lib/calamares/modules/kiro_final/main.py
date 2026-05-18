#!/usr/bin/env python3
"""
Calamares module for final system configuration and cleanup.
Handles permissions, file cleanup, bootloader configuration, and VM package removal.
"""

import os
import shutil
import subprocess
import time
import libcalamares


def remove_path(path):
    """Remove file or directory safely."""
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.exists(path):
            os.remove(path)
    except Exception as e:
        libcalamares.utils.warning(f"Failed to remove {path}: {e}")


def is_package_installed(package_name, target_root):
    """Check if a package is installed in the target system."""
    try:
        check = subprocess.run(
            ["chroot", target_root, "pacman", "-Q", package_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return check.returncode == 0
    except Exception as e:
        libcalamares.utils.warning(f"Failed to check package {package_name}: {e}")
        return False


def chroot_pacman_remove(target_root, packages):
    """Remove packages in the target system using pacman."""
    try:
        subprocess.run(
            ["chroot", target_root, "pacman", "-Rns", "--noconfirm"] + packages,
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        libcalamares.utils.warning(f"Failed to remove packages: {e}")
        return False


def chroot_disable_service(target_root, service):
    """Disable a systemd service in the target system."""
    subprocess.run(
        ["chroot", target_root, "systemctl", "disable", service],
        check=False
    )


def detect_virtualization(target_root):
    """Detect if system is running in a virtual machine."""
    try:
        result = subprocess.run(
            ["chroot", target_root, "systemd-detect-virt"],
            stdout=subprocess.PIPE,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception as e:
        libcalamares.utils.warning(f"Failed to detect virtualization: {e}")
        return "unknown"


def wait_for_pacman_lock(target_root, timeout=30):
    """Wait for pacman lock to be released, force remove if timeout exceeded."""
    lock_path = os.path.join(target_root, "var/lib/pacman/db.lck")
    waited = 0

    while os.path.exists(lock_path):
        if waited >= timeout:
            libcalamares.utils.debug(f"Pacman lock timeout after {timeout}s. Forcing removal.")
            try:
                os.remove(lock_path)
            except Exception as e:
                libcalamares.utils.warning(f"Could not remove pacman lock: {e}")
            break

        libcalamares.utils.debug("Pacman is locked. Waiting 5 seconds...")
        time.sleep(5)
        waited += 5

def run():
    """Execute final system configuration and cleanup."""
    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("Start kiro_final module")
    libcalamares.utils.debug("##############################################\n")

    libcalamares.utils.debug("This module will perform the following operations:")
    libcalamares.utils.debug("  1. Set permissions for security directories (sudoers.d, polkit-1)")
    libcalamares.utils.debug("  2. Copy /etc/skel to /root home directory")
    libcalamares.utils.debug("  3. Set /root permissions to 0o700")
    libcalamares.utils.debug("  4. Remove installation-related files and folders")
    libcalamares.utils.debug("  5. Configure system environment (EDITOR=nano)")
    libcalamares.utils.debug("  6. Configure Bluetooth and PulseAudio")
    libcalamares.utils.debug("  7. Check bootloader configuration (remove GRUB if systemd-boot detected)")
    libcalamares.utils.debug("  8. Detect virtualization and remove unnecessary VM packages")
    libcalamares.utils.debug("  9. Remove installer package (kiro-calamares-config)\n")

    target_root = libcalamares.globalstorage.value("rootMountPoint")
    results = {}

    # ========================
    # File System Configuration
    # ========================

    # Set directory permissions
    libcalamares.utils.debug("Setting permissions for security directories")
    try:
        os.chmod(os.path.join(target_root, "etc/sudoers.d"), 0o750)
        polkit_rules = os.path.join(target_root, "etc/polkit-1/rules.d")
        os.chmod(polkit_rules, 0o750)
        try:
            shutil.chown(polkit_rules, group="polkitd")
        except LookupError:
            libcalamares.utils.warning("Group 'polkitd' not found; skipping chown.")
        results["Set security directory permissions"] = "SUCCESS"
    except Exception as e:
        libcalamares.utils.warning(f"Failed to set permissions: {e}")
        results["Set security directory permissions"] = "FAILED"

    # Copy skeleton files to root home
    libcalamares.utils.debug("Copying /etc/skel to /root")
    try:
        skel = os.path.join(target_root, "etc/skel")
        root_home = os.path.join(target_root, "root")
        shutil.copytree(skel, root_home, dirs_exist_ok=True)
        results["Copy /etc/skel to /root"] = "SUCCESS"
    except Exception as e:
        libcalamares.utils.warning(f"Failed to copy /etc/skel to /root: {e}")
        results["Copy /etc/skel to /root"] = "FAILED"

    # Set root home permissions
    try:
        os.chmod(os.path.join(target_root, "root"), 0o700)
        results["Set /root permissions"] = "SUCCESS"
    except Exception as e:
        libcalamares.utils.warning(f"Failed to set /root permissions: {e}")
        results["Set /root permissions"] = "FAILED"

    # ========================
    # Cleanup Installation Files
    # ========================

    libcalamares.utils.debug("Removing unnecessary files and folders")
    try:
        paths_to_remove = [
            "etc/sudoers.d/g_wheel",
            "etc/polkit-1/rules.d/49-nopasswd_global.rules",
            "root/.automated_script.sh",
            "root/.zlogin",
            "etc/systemd/system/getty@tty1.service.d",  # Autologin cleanup
        ]
        for rel_path in paths_to_remove:
            remove_path(os.path.join(target_root, rel_path))
        results["Remove installation files"] = "SUCCESS"
    except Exception as e:
        libcalamares.utils.warning(f"Failed to remove installation files: {e}")
        results["Remove installation files"] = "FAILED"

    # ========================
    # System Configuration
    # ========================

    # Configure shell environment
    libcalamares.utils.debug("Configuring system environment")
    try:
        profile_path = os.path.join(target_root, "etc/profile")
        with open(profile_path, "a") as profile:
            profile.write("\nEDITOR=nano\n")
        results["Configure system environment"] = "SUCCESS"
    except Exception as e:
        libcalamares.utils.warning(f"Failed to write to /etc/profile: {e}")
        results["Configure system environment"] = "FAILED"

    # Configure Bluetooth and PulseAudio
    libcalamares.utils.debug("Configuring Bluetooth and audio")
    try:
        bt_conf = os.path.join(target_root, "etc/bluetooth/main.conf")
        pa_conf = os.path.join(target_root, "etc/pulse/default.pa")

        subprocess.run(
            ["sed", "-i", "s|#AutoEnable=true|AutoEnable=true|g", bt_conf],
            check=False
        )
        with open(pa_conf, "a") as pa:
            pa.write("\nload-module module-switch-on-connect\n")
        results["Configure Bluetooth and PulseAudio"] = "SUCCESS"
    except Exception as e:
        libcalamares.utils.warning(f"Failed to configure audio services: {e}")
        results["Configure Bluetooth and PulseAudio"] = "FAILED"

    # ========================
    # Bootloader Configuration
    # ========================

    libcalamares.utils.debug("Checking bootloader configuration")
    try:
        loader_conf = os.path.join(target_root, "boot/efi/loader/loader.conf")
        if os.path.exists(loader_conf):
            # systemd-boot is in use, remove GRUB
            libcalamares.utils.debug("systemd-boot detected. Removing GRUB")
            try:
                if is_package_installed("grub", target_root):
                    subprocess.run(
                        ["chroot", target_root, "pacman", "-R", "--noconfirm", "grub"],
                        check=True
                    )
            except Exception as e:
                libcalamares.utils.warning(f"Failed to remove GRUB: {e}")

            remove_path(os.path.join(target_root, "boot/grub"))

            # Remove GRUB configuration files
            try:
                grub_defaults_dir = os.path.join(target_root, "etc/default")
                grub_files = [f for f in os.listdir(grub_defaults_dir) if f.startswith("grub")]
                for grub_file in grub_files:
                    remove_path(os.path.join(grub_defaults_dir, grub_file))
            except Exception as e:
                libcalamares.utils.warning(f"Failed to remove GRUB defaults: {e}")
        results["Configure bootloader"] = "SUCCESS"
    except Exception as e:
        libcalamares.utils.warning(f"Failed to configure bootloader: {e}")
        results["Configure bootloader"] = "FAILED"

    # ========================
    # Virtual Machine Cleanup
    # ========================

    libcalamares.utils.debug("Checking for virtual machine environment")
    try:
        wait_for_pacman_lock(target_root)

        vm_type = detect_virtualization(target_root)
        libcalamares.utils.debug(f"Virtualization type: {vm_type}")

        # VMware cleanup (applies to oracle, kvm, vmware, none)
        if vm_type in ["oracle", "kvm", "vmware", "none"]:
            remove_path(os.path.join(target_root, "etc/xdg/autostart/vmware-user.desktop"))
            if is_package_installed("open-vm-tools", target_root):
                chroot_disable_service(target_root, "vmtoolsd.service")
                chroot_disable_service(target_root, "vmware-vmblock-fuse.service")
                chroot_pacman_remove(target_root, ["open-vm-tools"])
            if is_package_installed("xf86-video-vmware", target_root):
                chroot_pacman_remove(target_root, ["xf86-video-vmware"])
            remove_path(
                os.path.join(target_root, "etc/systemd/system/multi-user.target.wants/vmtoolsd.service")
            )

        # QEMU cleanup (applies to oracle, vmware, none)
        if vm_type in ["oracle", "vmware", "none"]:
            if is_package_installed("qemu-guest-agent", target_root):
                chroot_disable_service(target_root, "qemu-guest-agent.service")
                chroot_pacman_remove(target_root, ["qemu-guest-agent"])

        # VirtualBox cleanup (applies to kvm, vmware, none)
        if vm_type in ["kvm", "vmware", "none"]:
            for vbox_pkg in ["virtualbox-guest-utils", "virtualbox-guest-utils-nox"]:
                if is_package_installed(vbox_pkg, target_root):
                    chroot_disable_service(target_root, "vboxservice.service")
                    chroot_pacman_remove(target_root, [vbox_pkg])

        results["Virtual machine cleanup"] = "SUCCESS"
    except Exception as e:
        libcalamares.utils.warning(f"Failed during VM cleanup: {e}")
        results["Virtual machine cleanup"] = "FAILED"

    # ========================
    # Final Cleanup
    # ========================

    libcalamares.utils.debug("Removing installer package")
    try:
        subprocess.run(
            ["chroot", target_root, "pacman", "-R", "--noconfirm", "kiro-calamares-config"],
            check=True
        )
        results["Remove installer package"] = "SUCCESS"
    except subprocess.CalledProcessError as e:
        libcalamares.utils.warning(f"Failed to remove kiro-calamares-config: {e}")
        results["Remove installer package"] = "FAILED"

    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("End kiro_final module - Function Results:")
    for func_name, status in results.items():
        libcalamares.utils.debug(f"  {func_name}: {status}")
    libcalamares.utils.debug("##############################################\n")

    return None
