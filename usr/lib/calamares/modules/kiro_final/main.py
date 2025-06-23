#!/usr/bin/env python3

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

def detect_x11_session(target_root):
    """Detect the X11 session in the target system."""
    xsessions_path = os.path.join(target_root, "usr/share/xsessions")
    try:
        for entry in os.listdir(xsessions_path):
            if entry.endswith(".desktop"):
                return entry
    except Exception as e:
        libcalamares.utils.warning(f"Failed to detect X11 session: {e}")
    return None

def build_chadwm_for_user(target_root):
    """Build ChadWM for user with UID 1000 in the target system."""
    try:
        result = subprocess.run(
            ["chroot", target_root, "getent", "passwd", "1000"],
            capture_output=True,
            text=True,
            check=True
        )
        username = result.stdout.split(":")[0]
        config_path = f"/home/{username}/.config/arco-chadwm/chadwm"
        full_path = os.path.join(target_root, config_path)

        if os.path.isdir(full_path):
            libcalamares.utils.debug(f"Building ChadWM at {config_path}")
            subprocess.run(["make", "-B"], cwd=full_path, check=True)
            subprocess.run(["make", "install"], cwd=full_path, check=True)
        else:
            libcalamares.utils.warning(f"Directory {config_path} not found. Skipping ChadWM build.")
    except Exception as e:
        libcalamares.utils.warning(f"Failed to build ChadWM: {e}")

def run():
    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("Start kiro_final module")
    libcalamares.utils.debug("#################################\n")

    target_root = libcalamares.globalstorage.value("rootMountPoint")

    # --- Permissions of important folders ---
    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("Setting permissions for important folders")
    libcalamares.utils.debug("#################################\n")
    
    try:
        os.chmod(os.path.join(target_root, "etc/sudoers.d"), 0o750)
        polkit_rules = os.path.join(target_root, "etc/polkit-1/rules.d")
        os.chmod(polkit_rules, 0o750)
        try:
            shutil.chown(polkit_rules, group="polkitd")
        except LookupError:
            libcalamares.utils.warning("Group 'polkitd' not found; skipping chown.")

    except Exception as e:
        libcalamares.utils.warning(f"Failed to set permissions: {e}")

    # --- Copy /etc/skel to /root ---
    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("Copying /etc/skel to /root")
    libcalamares.utils.debug("#################################\n")

    try:
        skel = os.path.join(target_root, "etc/skel")
        root_home = os.path.join(target_root, "root")
        shutil.copytree(skel, root_home, dirs_exist_ok=True)
    except Exception as e:
        libcalamares.utils.warning(f"Failed to copy /etc/skel to /root: {e}")

    # --- Cleanup autologin root ---
    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("Remove autologin")
    libcalamares.utils.debug("#################################\n")

    autologin_path = os.path.join(target_root, "etc/systemd/system/getty@tty1.service.d")
    libcalamares.utils.debug("Cleaning up autologin for root")
    shutil.rmtree(autologin_path, ignore_errors=True)

    # --- Set editor to nano ---
    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("Nano as editor")
    libcalamares.utils.debug("#################################\n")
    profile_path = os.path.join(target_root, "etc/profile")
    libcalamares.utils.debug("Setting EDITOR=nano in /etc/profile")
    try:
        with open(profile_path, "a") as profile:
            profile.write("\nEDITOR=nano\n")
    except Exception as e:
        libcalamares.utils.warning(f"Failed to write to /etc/profile: {e}")

    # --- Bluetooth improvements ---
    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("Bluetooth")
    libcalamares.utils.debug("#################################\n")

    bt_conf = os.path.join(target_root, "etc/bluetooth/main.conf")
    pa_conf = os.path.join(target_root, "etc/pulse/default.pa")
    libcalamares.utils.debug("Enabling AutoEnable=true in bluetooth config")
    subprocess.run(["sed", "-i", "s|#AutoEnable=true|AutoEnable=true|g", bt_conf], check=False)
    libcalamares.utils.debug("Appending module-switch-on-connect to default.pa")
    try:
        with open(pa_conf, "a") as pa:
            pa.write("\nload-module module-switch-on-connect\n")
    except Exception as e:
        libcalamares.utils.warning(f"Failed to append to default.pa: {e}")

    # --- Cleanup original files ---
    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("Removing unnecessary files and folders")
    libcalamares.utils.debug("#################################\n")
    
    paths_to_remove = [
        "etc/sudoers.d/g_wheel",
        "usr/share/backgrounds/xfce",
        "etc/polkit-1/rules.d/49-nopasswd_global.rules",
        "root/.automated_script.sh",
        "root/.zlogin"
    ]
    for rel_path in paths_to_remove:
        remove_path(os.path.join(target_root, rel_path))

    # --- Set root permissions to 700 ---
    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("Setting permissions of /root to 700")
    libcalamares.utils.debug("#################################\n")
    
    try:
        os.chmod(os.path.join(target_root, "root"), 0o700)
    except Exception as e:
        libcalamares.utils.warning(f"Failed to set /root permissions: {e}")

    # --- Bootloader cleanup if systemd-boot is used ---
    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("Checking for systemd-boot setup")
    libcalamares.utils.debug("#################################\n")
 
    loader_conf = os.path.join(target_root, "boot/efi/loader/loader.conf")
    if os.path.exists(loader_conf):
        libcalamares.utils.debug("Detected systemd-boot. Removing GRUB...")
        try:
            if is_package_installed("grub", target_root):
                subprocess.run(["chroot", target_root, "pacman", "-R", "--noconfirm", "grub"], check=True)
        except Exception as e:
            libcalamares.utils.warning(f"Failed to remove GRUB: {e}")

        remove_path(os.path.join(target_root, "boot/grub"))

        grub_defaults = [f for f in os.listdir(os.path.join(target_root, "etc/default")) if f.startswith("grub")]
        for grub_file in grub_defaults:
            remove_path(os.path.join(target_root, "etc/default", grub_file))

    # --- Desktop-specific ChadWM logic ---
    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("Start chadwm build")
    libcalamares.utils.debug("#################################\n")

    desktop = detect_x11_session(target_root)
    if desktop is None:
        libcalamares.utils.debug("No X11 session detected.")
    elif desktop == "chadwm.desktop":
        libcalamares.utils.debug(f"Detected session file: {desktop}")
        libcalamares.utils.debug("Detected ChadWM session. Building ChadWM.")
        build_chadwm_for_user(target_root)
    else:
        libcalamares.utils.debug(f"No specific action for session: {desktop}")

    libcalamares.utils.debug("#################################")
    libcalamares.utils.debug("End chadwm build")
    libcalamares.utils.debug("#################################\n")

    # --- ArcoLinux virtual machine check ---
    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("Removing virtual machine packages")
    libcalamares.utils.debug("##############################################\n")

    # Wait for pacman lock
    lock_path = os.path.join(target_root, "var/lib/pacman/db.lck")
    waited = 0
    while os.path.exists(lock_path):
        libcalamares.utils.debug("Pacman is locked. Waiting 5 seconds...")
        time.sleep(5)
        waited += 5
        if waited >= 30:
            libcalamares.utils.debug("Removing pacman lock after timeout.")
            try:
                os.remove(lock_path)
            except Exception as e:
                libcalamares.utils.warning(f"Could not remove pacman lock: {e}")
            break

    # Detect virtualization
    try:
        result = subprocess.run(
            ["chroot", target_root, "systemd-detect-virt"],
            stdout=subprocess.PIPE,
            text=True,
            check=True
        )
        vm_type = result.stdout.strip()
        libcalamares.utils.debug(f"Detected virtualization: {vm_type}")
    except Exception as e:
        libcalamares.utils.warning(f"Failed to detect virtualization: {e}")
        vm_type = "unknown"

    def chroot_pacman_rm(packages):
        try:
            subprocess.run(
                ["chroot", target_root, "pacman", "-Rns", "--noconfirm"] + packages,
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            libcalamares.utils.warning(f"Failed to remove packages: {e}")
            return False

    def chroot_disable_service(service):
        subprocess.run(["chroot", target_root, "systemctl", "disable", service], check=False)

    def cleanup_files(paths):
        for path in paths:
            remove_path(os.path.join(target_root, path))

    if vm_type in ["oracle", "kvm", "vmware", "none"]:
        # Common VMware cleanup
        cleanup_files(["etc/xdg/autostart/vmware-user.desktop"])
        if is_package_installed("open-vm-tools", target_root):
            chroot_disable_service("vmtoolsd.service")
            chroot_disable_service("vmware-vmblock-fuse.service")
            chroot_pacman_rm(["open-vm-tools"])
        if is_package_installed("xf86-video-vmware", target_root):
            chroot_pacman_rm(["xf86-video-vmware"])
        cleanup_files(["etc/systemd/system/multi-user.target.wants/vmtoolsd.service"])

    if vm_type in ["oracle", "vmware", "none"]:
        # QEMU removal
        if is_package_installed("qemu-guest-agent", target_root):
            chroot_disable_service("qemu-guest-agent.service")
            chroot_pacman_rm(["qemu-guest-agent"])

    if vm_type in ["kvm", "vmware", "none"]:
        # VirtualBox cleanup
        for vbox_pkg in ["virtualbox-guest-utils", "virtualbox-guest-utils-nox"]:
            if is_package_installed(vbox_pkg, target_root):
                chroot_disable_service("vboxservice.service")
                chroot_pacman_rm([vbox_pkg])

    libcalamares.utils.debug("End ArcoLinux virtual machine check")

    # --- Remove kiro-calamares-config-next package ---
    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("Removing kiro-calamares-config-next package")
    libcalamares.utils.debug("##############################################\n")
    
    try:
        subprocess.run(
            ["chroot", target_root, "pacman", "-R", "--noconfirm", "kiro-calamares-config-next"],
            check=True
        )
    except subprocess.CalledProcessError as e:
        libcalamares.utils.warning(f"Failed to remove kiro-calamares-config-next: {e}")

    libcalamares.utils.debug("End removing kiro-calamares-config-next")

    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("End kiro_final module")
    libcalamares.utils.debug("##############################################\n")

    return None
