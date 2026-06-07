#!/usr/bin/env python3
"""
Calamares module for hardware-aware driver installation via chwd.

Runs `chwd --autoconfigure` inside the chroot to install the optimal driver
profile for the detected hardware (GPU, network adapter, microcode-aware
laptop tweaks, hybrid graphics, etc.).

Honours the boot-menu `driver=` kernel cmdline (three modes):
  - driver=free        -> skip chwd; kiro_remove_nvidia removed the baked NVIDIA
                          packages, system runs on mesa / the open stack.
  - driver=nonfree     -> skip chwd; keep the baked nvidia-open-dkms untouched
                          (the proven express lane for modern Turing+ GPUs).
  - driver=nonfreechwd -> run chwd; kiro_remove_nvidia already wiped the baked
                          nvidia-open-dkms first, so chwd installs exactly the
                          profile it detects (any card) with nothing to conflict.

driver=nonfreechwd is the only install path that fetches packages online (the
driver comes mainly from [cachyos], some from [chaotic-aur]). Before running chwd
we therefore make that fetch reliable: lead both repos with a trusted geo-CDN
mirror (the same ones build-scripts/host-prep.sh uses) and `pacman -Sy` to refresh
the chroot's stale sync databases. Both steps are best-effort and never abort.

If chwd cannot complete (e.g. a detected profile needs a package that is not
in the configured repos), the failure is treated as non-fatal: pacman's
transaction is atomic so nothing is installed, chwd's own pre_remove hook
removes any mkinitcpio drop-ins it wrote, and the install continues on the
open driver (nouveau/mesa). A breadcrumb is left at
/var/log/kiro-chwd-skipped.log so post-install audits can flag the skip.
"""

import os
import subprocess
import time

import libcalamares


status_update_time = 0

# Trusted geo-routed CDN mirrors — the same servers the build host relies on in
# build-scripts/host-prep.sh (KIRO_CURATED_*). driver=nonfreechwd is the only
# install path that fetches packages online, so before chwd pulls a driver we make
# sure its repos lead with a reliable CDN and sync fresh DBs. Keep these in step
# with host-prep.sh. NOTE: the two repos use different $repo/$arch path orders —
# do not "normalise" them.
_TRUSTED_MIRRORS = {
    "cachyos-mirrorlist": "Server = https://cdn77.cachyos.org/repo/$arch/$repo",
    "chaotic-mirrorlist": "Server = https://geo-mirror.chaotic.cx/$repo/$arch",
}


def pretty_name():
    return "Installing hardware drivers via chwd..."


def kernel_cmdline(param_name, default=None):
    """Parse /proc/cmdline for a parameter value."""
    try:
        with open("/proc/cmdline", "r") as f:
            params = f.read().strip().split()
        for param in params:
            if param.startswith(param_name + "="):
                return param.split("=", 1)[1]
            elif param == param_name:
                return ""
    except Exception as e:
        libcalamares.utils.debug(f"Error reading /proc/cmdline: {e}")
    return default


def line_cb(line):
    """Pipe chwd output into the Calamares debug log + tick progress."""
    global status_update_time
    libcalamares.utils.debug("chwd: " + line.strip())
    if (time.time() - status_update_time) > 0.5:
        libcalamares.job.setprogress(0)
        status_update_time = time.time()


def run_in_host(command, line_func):
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1,
    )
    for line in proc.stdout:
        if line.strip():
            line_func(line)
    proc.wait()
    if proc.returncode != 0:
        return ("chwd-failed", f"chwd exited with code {proc.returncode}")
    return None


def _record_skip(root_mount_point, detail):
    marker = os.path.join(root_mount_point, "var/log/kiro-chwd-skipped.log")
    try:
        with open(marker, "w") as f:
            f.write(
                "chwd was skipped during installation because it could not complete.\n"
                f"Reason: {detail}\n"
                "The system booted on the open driver (nouveau/mesa). To retry:\n"
                "  chwd --autoconfigure\n"
                "Some driver packages come only from the [cachyos] repo, which Kiro ships\n"
                "disabled by default. If the retry still cannot find a package, uncomment\n"
                "[cachyos] in /etc/pacman.conf first, then run chwd --autoconfigure again.\n"
            )
    except OSError as e:
        libcalamares.utils.warning(f"Could not write chwd skip marker: {e}")


def _ensure_cdn_first(mirrorlist_path, server_line):
    """Prepend the trusted CDN server unless it is already present in the file."""
    try:
        with open(mirrorlist_path, "r") as f:
            content = f.read()
    except OSError:
        return False
    url = server_line.split("=", 1)[1].strip()
    if url in content:
        return False
    header = (
        "# Prepended by Kiro chwd module — trusted CDN first so the driver install\n"
        "# pulls from a reliable mirror. See build-scripts/host-prep.sh.\n"
    )
    with open(mirrorlist_path, "w") as f:
        f.write(header + server_line + "\n\n" + content)
    return True


def _mirror_host(server_line):
    """Host part of a 'Server = https://host/path' line, for concise logging."""
    url = server_line.split("=", 1)[1].strip()
    return url.split("//", 1)[-1].split("/", 1)[0]


def _refresh_driver_mirrors(root_mount_point):
    """Best-effort: lead cachyos/chaotic with a trusted CDN, then sync DBs before chwd.

    chwd runs `pacman -S`, which does not refresh the sync databases; a fresh chroot's
    DBs can predate the ISO, so without this chwd may request a driver version the
    mirror no longer carries and fall back to the open driver. Never fatal.

    Logs a single greppable `chwd: ── mirror refresh ──` block so this step is easy to
    find in Calamares.log and is unmistakably distinct from kiro_before's own pacman -Sy.
    """
    libcalamares.utils.debug("chwd: ──────── mirror refresh ────────")
    for name, server_line in _TRUSTED_MIRRORS.items():
        path = os.path.join(root_mount_point, "etc/pacman.d", name)
        host = _mirror_host(server_line)
        try:
            if _ensure_cdn_first(path, server_line):
                libcalamares.utils.debug(f"chwd: led {name} → {host}")
            else:
                libcalamares.utils.debug(f"chwd: {name} unchanged (already CDN-led or absent)")
        except OSError as e:
            libcalamares.utils.warning(f"chwd: could not update {name}: {e}")

    try:
        result = subprocess.run(
            ["arch-chroot", root_mount_point, "pacman", "-Sy"],
            check=False,
            timeout=180,
        )
        if result.returncode == 0:
            libcalamares.utils.debug("chwd: pacman -Sy … OK")
        else:
            libcalamares.utils.warning(
                f"chwd: pacman -Sy exited {result.returncode} (non-fatal, continuing)"
            )
    except (subprocess.TimeoutExpired, OSError) as e:
        libcalamares.utils.warning(f"chwd: pacman -Sy refresh failed/timed out, continuing: {e}")
    libcalamares.utils.debug("chwd: ─────────────────────────────────")


def run():
    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("Start chwd")
    libcalamares.utils.debug("##############################################\n")

    selection = kernel_cmdline("driver", default="free")
    libcalamares.utils.debug(f"Kernel parameter 'driver' = {selection}")

    if selection != "nonfreechwd":
        libcalamares.utils.debug(
            f"Skipping chwd because 'driver={selection}' — chwd runs only on "
            "'driver=nonfreechwd'. (free → kiro_remove_nvidia cleaned up; "
            "nonfree → keep the baked nvidia-open-dkms.)"
        )
        return None

    root_mount_point = libcalamares.globalstorage.value("rootMountPoint")
    if not root_mount_point:
        return (
            "No mount point for root partition",
            "globalstorage does not contain a 'rootMountPoint' key.",
        )
    if not os.path.exists(root_mount_point):
        return (
            "Bad mount point for root partition",
            f"'{root_mount_point}' does not exist.",
        )

    _refresh_driver_mirrors(root_mount_point)

    chwd_command = ["arch-chroot", root_mount_point, "chwd", "--autoconfigure"]
    libcalamares.utils.debug(f"Running: {' '.join(chwd_command)}")

    error = run_in_host(chwd_command, line_cb)
    if error:
        _title, detail = error
        libcalamares.utils.warning(
            f"chwd did not complete ({detail}); continuing on the open "
            "driver (nouveau/mesa). The system is usable; proprietary "
            "drivers can be installed later with 'chwd --autoconfigure'."
        )
        _record_skip(root_mount_point, detail)
        libcalamares.job.setprogress(1.0)
        return None

    libcalamares.job.setprogress(1.0)

    libcalamares.utils.debug("##############################################")
    libcalamares.utils.debug("End chwd")
    libcalamares.utils.debug("##############################################\n")

    return None
