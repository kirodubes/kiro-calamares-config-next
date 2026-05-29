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
    # systemd-detect-virt exits 1 on bare metal (no virt found) while still
    # printing "none" to stdout, so we must not pass check=True.
    try:
        result = subprocess.run(
            ["chroot", target_root, "systemd-detect-virt"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip() or "unknown"
    except Exception as e:
        libcalamares.utils.warning(f"Failed to detect virtualization: {e}")
        return "unknown"


# Pacman hooks shadowed to /dev/null by kiro_before. Must stay in sync with
# kiro_before.SUPPRESSED_HOOKS.
SUPPRESSED_HOOKS = (
    "90-mkinitcpio-install.hook",
    "gtk-update-icon-cache.hook",
    "update-desktop-database.hook",
    "30-update-mime-database.hook",
    "fontconfig.hook",
    "dconf-update.hook",
    "xorg-mkfontscale.hook",
)

# Each suppressed hook's underlying command, run exactly ONCE in the target
# chroot at the very end of kiro_final after the symlinks are removed. The
# mkinitcpio hook has no entry here — Calamares' explicit initcpio job
# already rebuilt initramfs before kiro_final runs.
#
# Each tuple is (description, shell command, trigger dir relative to target
# root). The trigger dir is the same path the suppressed hook watches; we
# compare its current mtime against the baseline kiro_before snapshotted
# pre-install and SKIP rebuilds whose source data was never touched. Without
# the skip we paid ~8s/run for update-mime-database, ~2s for fc-cache, etc.,
# even though the install transactions (kiro_remove_nvidia, packages,
# kiro_ucode, kiro_final removals) typically don't touch MIME / fonts /
# dconf data at all. Two trigger dirs are shared (fontconfig + xorg-mkfontscale
# both watch usr/share/fonts) — that's fine, the mtime check is symmetric.
CACHE_REBUILD_STEPS = (
    ("gtk-update-icon-cache",
     'for d in /usr/share/icons/*/; do [ -e "${d}index.theme" ] && gtk-update-icon-cache -q "$d" || true; done',
     "usr/share/icons"),
    ("update-desktop-database",
     "update-desktop-database --quiet",
     "usr/share/applications"),
    ("update-mime-database",
     "update-mime-database /usr/share/mime",
     "usr/share/mime/packages"),
    ("fontconfig (fc-cache)",
     "fc-cache -s",
     "usr/share/fonts"),
    ("dconf update",
     "dconf update",
     "etc/dconf/db"),
    ("xorg-mkfontscale",
     'for d in /usr/share/fonts/*/; do [ "${d%/}" = /usr/share/fonts/encodings ] && continue; mkfontscale "$d" 2>/dev/null || true; mkfontdir "$d" 2>/dev/null || true; done',
     "usr/share/fonts"),
)


def restore_suppressed_hooks(target_root):
    """Unlink the /dev/null shadow symlinks placed by kiro_before."""
    hooks_dir = os.path.join(target_root, "etc/pacman.d/hooks")
    restored = 0
    for hook in SUPPRESSED_HOOKS:
        path = os.path.join(hooks_dir, hook)
        try:
            if os.path.islink(path) and os.readlink(path) == "/dev/null":
                os.unlink(path)
                libcalamares.utils.debug(f"Removed hook override: {path}")
                restored += 1
            else:
                libcalamares.utils.debug(f"Hook override not present, skipping: {path}")
        except Exception as e:
            libcalamares.utils.warning(f"Failed to restore {hook}: {e}")
    return restored


def _cache_trigger_changed(target_root, trigger_rel, baseline):
    """Return True if trigger_rel's mtime changed since kiro_before's snapshot.

    Defensive default: returns True (rebuild) when:
      - no baseline available (kiro_before didn't run, or globalstorage lost)
      - mtime cannot be read
      - dir came into / went out of existence

    Limits: only the trigger dir's own mtime is checked, not files inside its
    subdirs. That catches additions/removals at the watched level (which is
    what the pacman hook triggers on too) without an expensive recursive walk.
    """
    if not baseline:
        return True
    previous = baseline.get(trigger_rel)
    full = os.path.join(target_root, trigger_rel)
    try:
        current = os.stat(full).st_mtime if os.path.exists(full) else None
    except Exception:
        return True
    return current != previous


def rebuild_caches_once(target_root):
    """Run each suppressed hook's underlying command exactly once in the chroot.

    Skips rebuilds whose trigger dir mtime is unchanged vs kiro_before's
    snapshot — the typical Kiro install touches very few cache trigger paths,
    so update-mime-database / fc-cache / dconf / mkfontscale usually have
    nothing to do.
    """
    baseline = libcalamares.globalstorage.value("kiroCacheMtimeBaseline") or {}
    for desc, cmd, trigger_rel in CACHE_REBUILD_STEPS:
        if not _cache_trigger_changed(target_root, trigger_rel, baseline):
            libcalamares.utils.debug(f"Cache trigger unchanged, skipping rebuild: {desc}")
            continue
        libcalamares.utils.debug(f"Rebuilding cache once: {desc}")
        try:
            subprocess.run(
                ["chroot", target_root, "sh", "-c", cmd],
                check=False,
            )
        except Exception as e:
            libcalamares.utils.warning(f"Cache rebuild '{desc}' failed (continuing): {e}")


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


# Cleanup profiles for VM-related packages and orphan service symlinks.
# Each profile is what to strip when the target is NOT this kind of VM.
VM_CLEANUP_PROFILES = {
    "vmware": {
        "packages": ("open-vm-tools", "xf86-video-vmware"),
        "disable_services": ("vmtoolsd.service", "vmware-vmblock-fuse.service"),
        "orphan_symlinks": (
            "etc/systemd/system/multi-user.target.wants/vmtoolsd.service",
            "etc/systemd/system/multi-user.target.wants/vmware-vmblock-fuse.service",
        ),
        "extra_paths": ("etc/xdg/autostart/vmware-user.desktop",),
    },
    "qemu": {
        "packages": ("qemu-guest-agent",),
        "disable_services": ("qemu-guest-agent.service",),
        "orphan_symlinks": (
            "etc/systemd/system/multi-user.target.wants/qemu-guest-agent.service",
        ),
        "extra_paths": (),
    },
    "vbox": {
        "packages": ("virtualbox-guest-utils", "virtualbox-guest-utils-nox"),
        "disable_services": ("vboxservice.service",),
        "orphan_symlinks": (
            "etc/systemd/system/multi-user.target.wants/vboxservice.service",
        ),
        "extra_paths": (),
    },
}

# For each detected virt type, which profiles to clean up.
# Anything not listed (e.g. "qemu", "unknown") gets no cleanup — safer default
# than guessing and uninstalling the host's own guest tools.
VM_CLEANUP_BY_TYPE = {
    "none":   ("vmware", "qemu", "vbox"),  # bare metal — strip all
    "oracle": ("vmware", "qemu"),          # VirtualBox guest — keep vbox tools
    "kvm":    ("vmware", "vbox"),          # KVM guest — keep qemu-guest-agent
    "vmware": ("vmware", "qemu", "vbox"),  # preserved from prior behavior
}


def cleanup_vm_profile(target_root, profile_name):
    """Remove packages and orphan service symlinks for one VM profile."""
    profile = VM_CLEANUP_PROFILES[profile_name]
    installed = [p for p in profile["packages"] if is_package_installed(p, target_root)]
    if installed:
        for svc in profile["disable_services"]:
            chroot_disable_service(target_root, svc)
        chroot_pacman_remove(target_root, installed)
    # Symlinks and stray paths are removed unconditionally — `pacman -Rns`
    # does not unlink enable-time symlinks, and `systemctl disable` inside
    # the chroot is unreliable without a running dbus.
    for rel_path in profile["orphan_symlinks"] + profile["extra_paths"]:
        remove_path(os.path.join(target_root, rel_path))


def _disable_repo(target_root, repo):
    # Comment out a repo section (the [repo] header and its body lines) in the
    # target pacman.conf. Idempotent. See the call site for why cachyos is
    # disabled post-install rather than shipped disabled.
    pacman_conf = os.path.join(target_root, "etc/pacman.conf")
    header = f"[{repo}]"
    out = []
    in_section = False
    changed = False
    with open(pacman_conf) as f:
        lines = f.readlines()
    for line in lines:
        stripped = line.strip()
        if stripped == header:
            in_section = True
            out.append("#" + line)
            changed = True
            continue
        if in_section:
            if stripped == "" or stripped.startswith("["):
                in_section = False
            else:
                out.append("#" + line)
                changed = True
                continue
        out.append(line)
    if changed:
        with open(pacman_conf, "w") as f:
            f.writelines(out)
    return changed


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
    libcalamares.utils.debug("  7. Pin tuned ppd_base_profile = performance")
    libcalamares.utils.debug("  8. Disable [cachyos] repo in pacman.conf (opt-in on installed system)")
    libcalamares.utils.debug("  9. Check bootloader configuration (remove GRUB if systemd-boot detected)")
    libcalamares.utils.debug(" 10. Detect virtualization and remove unnecessary VM packages")
    libcalamares.utils.debug(" 11. Remove installer package (kiro-calamares-config)\n")

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
            "etc/systemd/logind.conf.d/do-not-suspend.conf",  # Live-only: keeps the installer awake; must not disable suspend/lid handling on the installed system
            "etc/mkinitcpio.d/linux.preset",             # Archiso live-only artifact; linux-lqx.preset from the kernel package is the correct one
            "etc/ssh/sshd_config.d/10-archiso.conf",
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
            profile.write("\nexport EDITOR=nano\n")
        results["Configure system environment"] = "SUCCESS"
    except Exception as e:
        libcalamares.utils.warning(f"Failed to write to /etc/profile: {e}")
        results["Configure system environment"] = "FAILED"

    # Configure Bluetooth and PulseAudio
    libcalamares.utils.debug("Configuring Bluetooth and audio")
    try:
        bt_conf = os.path.join(target_root, "etc/bluetooth/main.conf")
        pa_conf = os.path.join(target_root, "etc/pulse/default.pa")

        if os.path.exists(bt_conf):
            subprocess.run(
                ["sed", "-i", "s|#AutoEnable=true|AutoEnable=true|g", bt_conf],
                check=True
            )
        else:
            libcalamares.utils.warning(f"Bluetooth config not found: {bt_conf}")
        with open(pa_conf, "a") as pa:
            pa.write("\nload-module module-switch-on-connect\n")
        results["Configure Bluetooth and PulseAudio"] = "SUCCESS"
    except Exception as e:
        libcalamares.utils.warning(f"Failed to configure audio services: {e}")
        results["Configure Bluetooth and PulseAudio"] = "FAILED"

    # ========================
    # Power Profile Pinning
    # ========================

    # The tuned package's pacman install writes /etc/tuned/ppd_base_profile = balanced,
    # which short-circuits ppd.conf's `default=performance` fallback. Overwrite here in
    # kiro_final (last module) so the package's default does not survive the install.
    libcalamares.utils.debug("Pinning tuned ppd_base_profile = performance")
    try:
        ppd_base = os.path.join(target_root, "etc/tuned/ppd_base_profile")
        with open(ppd_base, "w") as f:
            f.write("performance\n")
        results["Pin tuned ppd_base_profile"] = "SUCCESS"
    except Exception as e:
        libcalamares.utils.warning(f"Failed to pin ppd_base_profile: {e}")
        results["Pin tuned ppd_base_profile"] = "FAILED"

    # ========================
    # Disable cachyos repo (opt-in on installed system)
    # ========================

    # cachyos must stay ENABLED during install so chwd can pull its driver
    # packages, so it can't ship disabled in the airootfs — we disable it here,
    # after chwd has run. Keeps `pacman -Syu` from silently swapping base
    # packages for cachyos rebuilds; chaotic-aur stays enabled and carries
    # linux-cachyos, so the default kernel still updates. Users re-enable cachyos
    # by uncommenting it. If chaotic-aur is ever dropped, revisit this: cachyos
    # would become the only source for linux-cachyos.
    libcalamares.utils.debug("Disabling [cachyos] repo in target pacman.conf")
    try:
        if _disable_repo(target_root, "cachyos"):
            results["Disable cachyos repo"] = "SUCCESS"
        else:
            results["Disable cachyos repo"] = "SUCCESS (already disabled)"
    except Exception as e:
        libcalamares.utils.warning(f"Failed to disable cachyos repo: {e}")
        results["Disable cachyos repo"] = "FAILED"

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

        profiles = VM_CLEANUP_BY_TYPE.get(vm_type, ())
        if not profiles:
            libcalamares.utils.debug(f"No VM cleanup profiles for vm_type={vm_type}")
        for profile_name in profiles:
            libcalamares.utils.debug(f"Applying VM cleanup profile: {profile_name}")
            cleanup_vm_profile(target_root, profile_name)

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
            ["chroot", target_root, "pacman", "-R", "--noconfirm", "kiro-calamares-config-next"],
            check=True
        )
        results["Remove installer package"] = "SUCCESS"
    except subprocess.CalledProcessError as e:
        libcalamares.utils.warning(f"Failed to remove kiro-calamares-config-next: {e}")
        results["Remove installer package"] = "FAILED"

    # ========================
    # Restore suppressed pacman hooks + rebuild caches once
    # ========================
    # MUST run after every pacman operation in this module and at the very end
    # of the install — leaving a /dev/null symlink behind would block the
    # corresponding cache rebuild on the user's first `pacman -Syu` (stale
    # initramfs/icons/MIME/fonts/dconf). Wrapped in their own try/except so an
    # earlier kiro_final failure cannot skip the restore.
    libcalamares.utils.debug("Restoring suppressed pacman hooks")
    try:
        restored = restore_suppressed_hooks(target_root)
        results["Restore suppressed hooks"] = f"SUCCESS ({restored}/{len(SUPPRESSED_HOOKS)})"
    except Exception as e:
        libcalamares.utils.warning(f"Failed to restore suppressed hooks: {e}")
        results["Restore suppressed hooks"] = "FAILED"

    libcalamares.utils.debug("Rebuilding caches once (post-install)")
    try:
        rebuild_caches_once(target_root)
        results["Rebuild caches once"] = "SUCCESS"
    except Exception as e:
        libcalamares.utils.warning(f"Failed during cache rebuild: {e}")
        results["Rebuild caches once"] = "FAILED"

    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("End kiro_final module - Function Results:")
    for func_name, status in results.items():
        libcalamares.utils.debug(f"  {func_name}: {status}")
    libcalamares.utils.debug("##############################################\n")

    return None
