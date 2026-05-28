#!/bin/bash
set -euo pipefail
#####################################################################
# Author    : Erik Dubois
# Website   : https://www.erikdubois.be
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
git_pull_if_repo() {
    if [[ -d "${SCRIPT_DIR}/.git" ]]; then
        log_section "Updating with git pull"
        git -C "${SCRIPT_DIR}" pull
    fi
}

bump_version() {
    local pkgbuild="${SCRIPT_DIR}/PKGBUILD"
    [[ ! -f "${pkgbuild}" ]] && { log_error "No PKGBUILD found in ${SCRIPT_DIR}"; exit 1; }

    local pkgname old_pkgver old_pkgrel new_pkgver new_pkgrel
    pkgname=$(grep -E '^pkgname=' "${pkgbuild}" | cut -d= -f2)
    old_pkgver=$(grep -E '^pkgver=' "${pkgbuild}" | cut -d= -f2)
    old_pkgrel=$(grep -E '^pkgrel=' "${pkgbuild}" | cut -d= -f2)

    if [[ ! "${old_pkgver}" =~ ^[0-9]{2}\.[0-9]{2}$ ]]; then
        log_info "Upstream-versioned package (pkgver=${old_pkgver}) — skipping bump"
        return 0
    fi

    local source_line
    source_line=$(grep -E '^\s*source=' "${pkgbuild}" || true)
    if echo "${source_line}" | grep -qE '\$\{?pkgver\}?|\$\{?pkgrel\}?'; then
        log_warn "Source URL embeds pkgver/pkgrel — skipping auto-bump for '${pkgname}'. Set version manually when a new upstream release is published."
        return 0
    fi

    new_pkgver=$(date +%y.%m)

    if [[ "${new_pkgver}" != "${old_pkgver}" ]]; then
        new_pkgrel="01"
    else
        new_pkgrel=$(printf '%02d' $((10#${old_pkgrel} + 1)))
    fi

    sed -i "s/^pkgver=.*/pkgver=${new_pkgver}/" "${pkgbuild}"
    sed -i "s/^pkgrel=.*/pkgrel=${new_pkgrel}/" "${pkgbuild}"

    log_info "Updated '${pkgname}':
  pkgver: ${old_pkgver} → ${new_pkgver}
  pkgrel: ${old_pkgrel} → ${new_pkgrel}"
}

create_current_version() {
    local pkgbuild="${SCRIPT_DIR}/PKGBUILD"
    local pkgver pkgrel epoch
    pkgver=$(grep -m1 "pkgver" "${pkgbuild}" | cut -d= -f2)
    pkgrel=$(grep -m1 "pkgrel" "${pkgbuild}" | cut -d= -f2)
    epoch=$(grep -m1 "epoch"  "${pkgbuild}" | cut -d= -f2 || true)
    {
        echo "pkgver=${pkgver}"
        echo "pkgrel=${pkgrel}"
        echo "epoch=${epoch}"
    } > "${SCRIPT_DIR}/.current-version"
}

check_version() {
    local pkgbuild="${SCRIPT_DIR}/PKGBUILD"
    local prev="${SCRIPT_DIR}/.previous-version"
    local pkgname pkgver pkgrel epoch
    local oldpkgver="" oldpkgrel="" oldepoch=""

    pkgname=$(grep -E '^pkgname=' "${pkgbuild}" | cut -d= -f2)
    pkgver=$(grep -m1 "pkgver" "${pkgbuild}" | cut -d= -f2)
    pkgrel=$(grep -m1 "pkgrel" "${pkgbuild}" | cut -d= -f2)
    epoch=$(grep -m1 "epoch"  "${pkgbuild}" | cut -d= -f2 || true)

    if [[ -f "${prev}" ]]; then
        oldpkgver=$(grep -m1 "pkgver" "${prev}" | cut -d= -f2 || true)
        oldpkgrel=$(grep -m1 "pkgrel" "${prev}" | cut -d= -f2 || true)
        oldepoch=$(grep -m1  "epoch"  "${prev}" | cut -d= -f2 || true)
    fi

    log_info "$(printf 'Previous: pkgver=%s pkgrel=%s epoch=%s\nNew:      pkgver=%s pkgrel=%s epoch=%s\nPackage:  %s' \
        "${oldpkgver}" "${oldpkgrel}" "${oldepoch}" \
        "${pkgver}"    "${pkgrel}"    "${epoch}" \
        "${pkgname}")"

    {
        echo "pkgver=${pkgver}"
        echo "pkgrel=${pkgrel}"
        echo "epoch=${epoch}"
    } > "${SCRIPT_DIR}/.current-version"

    if [[ "${pkgver}" != "${oldpkgver}" || "${pkgrel}" != "${oldpkgrel}" || "${epoch}" != "${oldepoch}" ]]; then
        BUILD_NEEDED="true"
    else
        BUILD_NEEDED="false"
    fi
}

build_package() {
    local pkgbuild="${SCRIPT_DIR}/PKGBUILD"
    local search destiny CHROOT CHOICE
    local makepkglist=""

    search="$(basename "${SCRIPT_DIR}")"
    destiny="${HOME}/KIRO/kiro_repo/x86_64/"
    CHROOT="${HOME}/Documents/chroot-archlinux"
    CHOICE=2

    for i in ${makepkglist}; do
        [[ "${search}" == "${i}" ]] && CHOICE=2
    done

    [[ -d /tmp/tempbuild ]] && rm -rf /tmp/tempbuild
    mkdir /tmp/tempbuild
    cp -r "${SCRIPT_DIR}/"* /tmp/tempbuild/

    local success="false"

    if [[ "${CHOICE}" == "1" ]]; then
        log_section "Building ${search} in CHROOT ${CHROOT}"
        arch-nspawn "${CHROOT}/root" pacman -Syu --noconfirm
        if (cd /tmp/tempbuild && makechrootpkg -c -r "${CHROOT}"); then
            success="true"
        fi
    else
        log_section "Building ${search} with MAKEPKG"
        if (cd /tmp/tempbuild && makepkg -s); then
            success="true"
        fi
    fi

    if [[ "${success}" == "true" ]]; then
        log_section "Copying packages to ${destiny}"
        cp -nv /tmp/tempbuild/*"${search}"*pkg.tar.zst "${destiny}" || \
            log_warn "${search} already exists in destination — skipping copy"

        local file_count
        file_count=$(find "${destiny}" -maxdepth 1 -name "${search}*" -print | wc -l)
        if [[ "${file_count}" -gt 2 ]]; then
            printf "%s\n" "${search}" | tee -a /tmp/installed
            find "${destiny}" -maxdepth 1 -name "${search}*" -exec basename {} \; | tee -a /tmp/installed
        fi

        # Push kiro_repo so the new package lands on the remote.
        # Non-fatal — a push failure logs a warning but doesn't abort the
        # build; pacman repo-db (repo.sh) registration is a separate step.
        local repo_up="${HOME}/KIRO/kiro_repo/up.sh"
        if [[ -x "${repo_up}" ]]; then
            log_section "Pushing kiro_repo"
            bash "${repo_up}" || log_warn "kiro_repo up.sh failed — push manually"
        else
            log_warn "kiro_repo up.sh not found at ${repo_up} — skipping repo push"
        fi
    fi

    log_section "Cleaning up"
    find "${SCRIPT_DIR}" -maxdepth 1 \( -name "*.log" -o -name "*.deb" -o -name "*.tar.gz" \) -delete

    cp "${SCRIPT_DIR}/.current-version" "${SCRIPT_DIR}/.previous-version"

    log_success "Build done for ${search}"
}

#####################################################################
# Main
#####################################################################
BUILD_NEEDED="false"

main() {
    git_pull_if_repo
    bump_version
    create_current_version
    check_version

    if [[ "${BUILD_NEEDED}" == "false" ]]; then
        log_warn "No version change detected — skipping build"
        exit 0
    fi

    build_package

    log_success "$(basename "$0") done"
}

main "$@"
