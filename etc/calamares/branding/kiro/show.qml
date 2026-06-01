/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2015 Teo Mrnjavac <teo@kde.org>
 *   SPDX-FileCopyrightText: 2018 Adriaan de Groot <groot@kde.org>
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Kiro install-time slideshow: brand-aligned text slides (no screenshots).
 *   All copy is sourced from the Kiro website feature list.
 */

import QtQuick
import calamares.slideshow 1.0

Presentation
{
    id: presentation

    fontFamily: "Noto Sans"
    titleColor: "#F1F5F9"
    textColor: "#CBD5E1"

    // Kiro brand backdrop behind every slide: near-black slate gradient.
    Rectangle {
        anchors.fill: parent
        z: -1
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#020617" }
            GradientStop { position: 1.0; color: "#0F172A" }
        }
    }

    function nextSlide() {
        presentation.goToNextSlide();
    }

    Timer {
        id: advanceTimer
        interval: 10000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: nextSlide()
    }

    // ── Title / closing slide: wordmark + tagline ──────────────────────────
    component KiroTitleSlide: Slide {
        property string wordmark: "Kiro"
        property string tagline: ""

        x: 0; y: 0
        width: masterWidth; height: masterHeight

        Column {
            anchors.centerIn: parent
            width: parent.width * 0.9
            spacing: masterHeight * 0.035
            opacity: parent.visible ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: 600; easing.type: Easing.OutCubic } }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: wordmark
                color: "#F8FAFC"
                font.family: "Noto Sans"; font.bold: true
                font.pixelSize: masterHeight * 0.11
                font.letterSpacing: 2
            }
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: masterHeight * 0.14; height: 4; radius: 2
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "#0EA5E9" }
                    GradientStop { position: 1.0; color: "#34D399" }
                }
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width
                text: tagline
                color: "#94A3B8"
                font.family: "Noto Sans"
                font.pixelSize: masterHeight * 0.033
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }
        }
    }

    // ── Feature slide: kicker + headline + divider + verified lines ────────
    component KiroSlide: Slide {
        property string kicker: ""
        property string headline: ""
        property var lines: []

        x: 0; y: 0
        width: masterWidth; height: masterHeight

        Column {
            anchors.centerIn: parent
            width: parent.width * 0.86
            spacing: masterHeight * 0.03
            opacity: parent.visible ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: 600; easing.type: Easing.OutCubic } }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                visible: kicker.length > 0
                text: kicker
                color: "#38BDF8"
                font.family: "Noto Sans"; font.bold: true
                font.pixelSize: masterHeight * 0.022
                font.letterSpacing: 3
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width
                text: headline
                color: "#F1F5F9"
                font.family: "Noto Sans"; font.bold: true
                font.pixelSize: masterHeight * 0.055
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: masterHeight * 0.09; height: 3; radius: 2
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "#0EA5E9" }
                    GradientStop { position: 1.0; color: "#34D399" }
                }
            }
            Column {
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width * 0.82
                spacing: masterHeight * 0.018
                Repeater {
                    model: lines
                    Text {
                        width: parent.width
                        text: modelData
                        color: "#CBD5E1"
                        font.family: "Noto Sans"
                        font.pixelSize: masterHeight * 0.027
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }

    KiroTitleSlide {
        wordmark: "Kiro"
        tagline: "An Arch-based Linux distribution — without the setup."
    }

    KiroSlide {
        kicker: "Open & teachable"
        headline: "Arch Linux, with a teacher in the box"
        lines: [
            "The distro you can watch being made — every step, on YouTube.",
            "Fork it, rebuild it, ship your own ISO.",
            "Free and open, always. No telemetry, no agenda."
        ]
    }

    KiroSlide {
        kicker: "Learn & grow"
        headline: "Use Kiro today, master Linux for life."
        lines: [
            "Real Arch underneath — what you learn here, you keep.",
            "Hundreds of video tutorials to level up at your own pace.",
            "From your first install to building your own ISO."
        ]
    }

    KiroSlide {
        kicker: "Pure Arch"
        headline: "Arch underneath, curated above"
        lines: [
            "Full pacman, rolling release, complete AUR access.",
            "No fork, no surprises — just Arch, made approachable."
        ]
    }

    KiroSlide {
        kicker: "Software"
        headline: "Everything ready to install"
        lines: [
            "Chaotic-aur enabled by default — thousands of AUR packages as pre-built binaries.",
            "Yay, paru and the pamac-aur GUI built in.",
            "Erik's nemesis_repo enabled out of the box."
        ]
    }

    KiroSlide {
        kicker: "ArchLinux Tweak Tool"
        headline: "Your Arch, one click at a time."
        lines: [
            "The GUI for the tweaks you'd otherwise hunt down in the wiki.",
            "Kernels, services, fixes and settings — point and click.",
            "Swap between 13 desktops on demand."
        ]
    }

    KiroSlide {
        kicker: "Alacritty-tweak-tool"
        headline: "Point, click, done. Your terminal, dialed in."
        lines: [
            "Fonts, colours, opacity and themes — set in a window, not a TOML file.",
            "Every Alacritty setting in one place, no config hunting."
        ]
    }

    KiroSlide {
        kicker: "Archlinux-logout"
        headline: "Go out in style."
        lines: [
            "Log out, lock, reboot, suspend or shut down — one clean screen.",
            "Every way to leave, a keystroke away."
        ]
    }

    KiroSlide {
        kicker: "Hardware"
        headline: "Detects your hardware. Sorts the rest."
        lines: [
            "The right CPU microcode, installed automatically.",
            "NVIDIA drivers if you need them.",
            "Running in a VM? The guest tools sort themselves out."
        ]
    }

    KiroSlide {
        kicker: "Performance"
        headline: "Tuned for speed"
        lines: [
            "Faster boot, snappier apps, smoother under heavy load.",
            "The speed tuning is done before you ever log in.",
            "Prefer a different kernel later? Swap it anytime."
        ]
    }

    KiroSlide {
        kicker: "Desktop"
        headline: "Your desktop, your way"
        lines: [
            "Xfce and Ohmychadwm ready at first login.",
            "13 desktops — 7 tilers, 6 full DEs — on demand from ATT."
        ]
    }

    KiroSlide {
        kicker: "Design"
        headline: "Eye candy, out of the box."
        lines: [
            "Curated themes, icons and wallpapers — already set up for you.",
            "Consistent and polished from the very first login.",
            "No ricing required."
        ]
    }

    KiroSlide {
        kicker: "Security"
        headline: "Secure and resilient"
        lines: [
            "Firewalld enabled by default.",
            "A sysctl hardening layer, already applied.",
            "No telemetry — your data stays on your machine."
        ]
    }

    KiroSlide {
        kicker: "Rollback"
        headline: "Break something? Roll back in minutes."
        lines: [
            "Timeshift snapshots, ready from day one.",
            "A bad update or a wrong move — just undo it.",
            "Experiment freely. You can always go back."
        ]
    }

    KiroSlide {
        kicker: "Learn as you go"
        headline: "Stuck? There's already a video for that."
        lines: [
            "Step-by-step video tutorials for nearly every task.",
            "Install, customize, troubleshoot — all on screen.",
            "The manual is a playlist."
        ]
    }

    KiroTitleSlide {
        wordmark: "Enjoy Kiro"
        tagline: "Sit back — your new system is being installed."
    }

    function onActivate() {
        presentation.currentSlide = 0;
    }

    function onLeave() {
    }
}
