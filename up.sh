#!/bin/bash
set -euo pipefail
#####################################################################
# Author    : Erik Dubois
# Website   : https://kiroproject.be
#####################################################################
#
#   DO NOT JUST RUN THIS. EXAMINE AND JUDGE. RUN AT YOUR OWN RISK.
#
#####################################################################

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

#####################################################################
# Colors
#####################################################################
if command -v tput >/dev/null 2>&1 && [[ -t 1 ]]; then
    RED="$(tput setaf 1)"
    GREEN="$(tput setaf 2)"
    YELLOW="$(tput setaf 3)"
    BLUE="$(tput setaf 4)"
    CYAN="$(tput setaf 6)"
    RESET="$(tput sgr0)"
else
    RED="" GREEN="" YELLOW="" BLUE="" CYAN="" RESET=""
fi

#####################################################################
# Logging
#####################################################################
log_section() {
    echo
    echo "${GREEN}############################################################################${RESET}"
    echo "$1"
    echo "${GREEN}############################################################################${RESET}"
    echo
}

log_info() {
    echo
    echo "${BLUE}############################################################################${RESET}"
    echo "$1"
    echo "${BLUE}############################################################################${RESET}"
    echo
}

log_warn() {
    echo
    echo "${YELLOW}############################################################################${RESET}"
    echo "$1"
    echo "${YELLOW}############################################################################${RESET}"
    echo
}

log_error() {
    echo
    echo "${RED}############################################################################${RESET}"
    echo "$1"
    echo "${RED}############################################################################${RESET}"
    echo
}

log_success() {
    echo
    echo "${GREEN}############################################################################${RESET}"
    echo "$1"
    echo "${GREEN}############################################################################${RESET}"
    echo
}

#####################################################################
# Error handling
#####################################################################
on_error() {
    local lineno="$1"
    local cmd="$2"
    echo
    echo "${RED}ERROR on line ${lineno}: ${cmd}${RESET}"
    echo
    sleep 10
}

trap 'on_error "$LINENO" "$BASH_COMMAND"' ERR

#####################################################################
# Functions
#####################################################################
clean_pycache() {
    local found
    found=$(find "${SCRIPT_DIR}" -type d -name "__pycache__" 2>/dev/null)

    if [[ -n "${found}" ]]; then
        log_section "Cleaning __pycache__"
        find "${SCRIPT_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        log_success "__pycache__ removed"
    fi
}

git_pull() {
    log_section "Git pull"
    git -C "${SCRIPT_DIR}" pull || log_warn "Git pull failed — continuing with local state"
}

# Fetch the latest amd-ucode / intel-ucode from the pacman repos and replace the
# bundled copies in etc/calamares/packages/. Relies on the local sync db, so it
# only sees a newer version after a `sudo pacman -Sy`.
update_ucode() {
    local pkg_dir="${SCRIPT_DIR}/etc/calamares/packages"
    local pkg url newfile

    log_section "Updating microcode packages"

    if ! command -v curl >/dev/null 2>&1; then
        log_warn "curl not found — skipping microcode update"
        return 0
    fi

    for pkg in amd-ucode intel-ucode; do
        url="$(pacman -Sp "${pkg}" 2>/dev/null || true)"
        if [[ -z "${url}" ]]; then
            log_warn "Could not resolve ${pkg} URL — sync the pacman db (sudo pacman -Sy) and retry"
            continue
        fi

        newfile="$(basename "${url}")"
        if [[ -f "${pkg_dir}/${newfile}" ]]; then
            log_info "${pkg} already current (${newfile})"
            continue
        fi

        log_info "Fetching ${newfile}"
        if ! curl -fL --retry 3 -o "${pkg_dir}/${newfile}" "${url}"; then
            log_error "Download of ${newfile} failed — skipping ${pkg}"
            rm -f "${pkg_dir}/${newfile}"
            continue
        fi
        if ! curl -fL --retry 3 -o "${pkg_dir}/${newfile}.sig" "${url}.sig"; then
            log_warn "Signature for ${newfile} unavailable — removing partial package"
            rm -f "${pkg_dir}/${newfile}" "${pkg_dir}/${newfile}.sig"
            continue
        fi

        # Drop the old versions of this package, keeping the one just downloaded.
        find "${pkg_dir}" -maxdepth 1 -type f -name "${pkg}-*.pkg.tar.zst*" \
            ! -name "${newfile}" ! -name "${newfile}.sig" -delete

        log_success "Updated ${pkg} → ${newfile}"
    done
}

# Copy the latest hand-built PKGBUILD folder from the KIRO-PKG-BUILD repo into
# etc/calamares/pkgbuild/. Only folders starting with "calamares-3" are considered,
# so the "calamares-next-*" beta folders (which belong to the -next config repo) are
# skipped. The highest version wins (sort -V). Source is left untouched.
#
# up.sh, setup.sh, .current-version and .previous-version belong to KIRO-PKG-BUILD,
# not the config repo, so they are stripped from the destination after the copy.
# Same for makepkg's build artifacts (calamares/ bare clone from the git source,
# plus pkg/ and src/ build dirs) — if updpkgsums or makepkg has run in the source
# folder, those would balloon the resulting .pkg.tar.zst (observed 2026-05-28:
# kiro-calamares-config-26.05-54 hit 97 MB, GitHub's 50 MB push warning fired).
# rm -rf so directories are removed too. Stripping unconditionally also clears
# any remnants left by earlier syncs.
update_pkgbuild() {
    local src_root="${HOME}/KIRO-PKG-BUILD"
    local dst="${SCRIPT_DIR}/etc/calamares/pkgbuild"
    local strip=(up.sh setup.sh .current-version .previous-version calamares pkg src)
    local latest f

    log_section "Syncing PKGBUILD from ${src_root}"

    if [[ ! -d "${src_root}" ]]; then
        log_warn "${src_root} not found — skipping PKGBUILD sync"
        return 0
    fi

    latest="$(find "${src_root}" -maxdepth 1 -type d -name 'calamares-next-*' -printf '%f\n' 2>/dev/null | sort -V | tail -1)"
    if [[ -z "${latest}" ]]; then
        log_warn "No calamares-next-* folder found in ${src_root} — skipping PKGBUILD sync"
        return 0
    fi

    log_info "Latest build folder: ${latest}"
    mkdir -p "${dst}"
    cp -af "${src_root}/${latest}/." "${dst}/"

    for f in "${strip[@]}"; do
        rm -rf "${dst}/${f}"
    done

    log_success "PKGBUILD synced from ${latest}"
}

ensure_git_remote_configured() {
    local remote_url
    if ! git -C "${SCRIPT_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        log_error "${SCRIPT_DIR} is not a git repository — up.sh must be run from inside a project repo"
        exit 1
    fi
    remote_url="$(git -C "${SCRIPT_DIR}" remote get-url origin 2>/dev/null || true)"
    if [[ "${remote_url}" != git@* ]]; then
        log_warn "Git remote is not SSH (${remote_url:-unset}) — running setup.sh to fix"
        bash "${SCRIPT_DIR}/setup.sh"
    fi
}

git_commit_and_push() {
    local branch

    log_section "Git add / commit / push"
    git -C "${SCRIPT_DIR}" add --all .

    if [[ -z "$(git -C "${SCRIPT_DIR}" status --porcelain)" ]]; then
        log_info "Nothing to commit — working tree clean"
    else
        git -C "${SCRIPT_DIR}" commit -m "update" || log_error "Git commit failed"
    fi

    branch="$(git -C "${SCRIPT_DIR}" rev-parse --abbrev-ref HEAD)"

    if ! git -C "${SCRIPT_DIR}" push -u origin "${branch}"; then
        log_warn "Push rejected — rebasing on remote changes and retrying"
        git -C "${SCRIPT_DIR}" pull --rebase origin "${branch}" || { log_error "Rebase failed — resolve conflicts manually"; return 1; }
        git -C "${SCRIPT_DIR}" push -u origin "${branch}" || log_error "Git push failed after rebase"
    fi
}

#####################################################################
# Main
#####################################################################
main() {
    ensure_git_remote_configured
    git_pull
    clean_pycache
    update_ucode
    update_pkgbuild

    if [[ -f "${SCRIPT_DIR}/chaotic.sh" ]]; then
        log_section "Running chaotic.sh"
        bash "${SCRIPT_DIR}/chaotic.sh"
    fi

    if [[ -f "${SCRIPT_DIR}/repo.sh" ]]; then
        log_section "Running repo.sh"
        bash "${SCRIPT_DIR}/repo.sh"
    fi

    git_commit_and_push

    log_success "$(basename "$0") done"
}

main "$@"
