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
        tagline: qsTr("An Arch-based Linux distribution — without the setup.")
    }

    KiroSlide {
        kicker: qsTr("Open & teachable")
        headline: qsTr("Arch Linux, with a teacher in the box")
        lines: [
            qsTr("The distro you can watch being made — every step, on YouTube."),
            qsTr("Fork it, rebuild it, ship your own ISO."),
            qsTr("Kiro: free and open, always. KiroTux: made possible by donations. No telemetry, no agenda.")
        ]
    }

    KiroSlide {
        kicker: qsTr("Learn & grow")
        headline: qsTr("Use Kiro today, master Linux for life.")
        lines: [
            qsTr("Real Arch underneath — what you learn here, you keep."),
            qsTr("Hundreds of video tutorials to level up at your own pace."),
            qsTr("From your first install to building your own ISO.")
        ]
    }

    KiroSlide {
        kicker: qsTr("Pure Arch")
        headline: qsTr("Arch underneath, curated above")
        lines: [
            qsTr("Full pacman, rolling release, complete AUR access."),
            qsTr("No fork, no surprises — just Arch, made approachable.")
        ]
    }

    KiroSlide {
        kicker: qsTr("Software")
        headline: qsTr("Everything ready to install")
        lines: [
            qsTr("Chaotic-aur enabled by default — thousands of AUR packages as pre-built binaries."),
            qsTr("Yay, paru and the pamac-aur GUI built in."),
            qsTr("Erik's nemesis_repo enabled out of the box.")
        ]
    }

    KiroSlide {
        kicker: "ArchLinux Tweak Tool"
        headline: qsTr("Your Arch, one click at a time.")
        lines: [
            qsTr("The GUI for the tweaks you'd otherwise hunt down in the wiki."),
            qsTr("Kernels, services, fixes and settings — point and click."),
            qsTr("Swap between 29 desktops on demand.")
        ]
    }

    KiroSlide {
        kicker: "Alacritty-tweak-tool"
        headline: qsTr("Point, click, done. Your terminal, dialed in.")
        lines: [
            qsTr("Fonts, colours, opacity and themes — set in a window, not a TOML file."),
            qsTr("Every Alacritty setting in one place, no config hunting.")
        ]
    }

    KiroSlide {
        kicker: "Fish-tweak-tool"
        headline: qsTr("A smarter shell, set up for you.")
        lines: [
            qsTr("Install a modern prompt: Tide, Starship, Hydro or Pure."),
            qsTr("Toggle plugins, pick a colour theme, manage your abbreviations.")
        ]
    }

    KiroSlide {
        kicker: "Fastfetch-tweak-tool"
        headline: qsTr("Your system info, your way.")
        lines: [
            qsTr("Pick modules, reorder them, choose from 500+ logos."),
            qsTr("See the result live as you tweak.")
        ]
    }

    KiroSlide {
        kicker: "Archlinux-logout"
        headline: qsTr("Go out in style.")
        lines: [
            qsTr("Log out, lock, reboot, suspend or shut down — one clean screen."),
            qsTr("Every way to leave, a keystroke away.")
        ]
    }

    KiroSlide {
        kicker: qsTr("Hardware")
        headline: qsTr("Detects your hardware. Sorts the rest.")
        lines: [
            qsTr("The right CPU microcode, installed automatically."),
            qsTr("NVIDIA drivers if you need them."),
            qsTr("Running in a VM? The guest tools sort themselves out.")
        ]
    }

    KiroSlide {
        kicker: qsTr("Performance")
        headline: qsTr("Tuned for speed")
        lines: [
            qsTr("Faster boot, snappier apps, smoother under heavy load."),
            qsTr("The speed tuning is done before you ever log in."),
            qsTr("Prefer a different kernel later? Swap it anytime.")
        ]
    }

    KiroSlide {
        kicker: qsTr("Desktop")
        headline: qsTr("Your desktop, your way")
        lines: [
            qsTr("Xfce and Ohmychadwm ready at first login."),
            qsTr("29 desktops — 6 full DEs, 9 tilers, 14 Wayland sessions — on demand from ATT.")
        ]
    }

    KiroSlide {
        kicker: qsTr("Design")
        headline: qsTr("Eye candy, out of the box.")
        lines: [
            qsTr("Curated themes, icons and wallpapers — already set up for you."),
            qsTr("Consistent and polished from the very first login."),
            qsTr("No ricing required.")
        ]
    }

    KiroSlide {
        kicker: qsTr("Security")
        headline: qsTr("Secure and resilient")
        lines: [
            qsTr("Firewalld enabled by default."),
            qsTr("A sysctl hardening layer, already applied."),
            qsTr("No telemetry — your data stays on your machine.")
        ]
    }

    KiroSlide {
        kicker: qsTr("Rollback")
        headline: qsTr("Break something? Roll back in minutes.")
        lines: [
            qsTr("Timeshift snapshots, ready from day one."),
            qsTr("A bad update or a wrong move — just undo it."),
            qsTr("Experiment freely. You can always go back.")
        ]
    }

    KiroSlide {
        kicker: qsTr("Learn as you go")
        headline: qsTr("Stuck? There's already a video for that.")
        lines: [
            qsTr("Step-by-step video tutorials for nearly every task."),
            qsTr("Install, customize, troubleshoot — all on screen."),
            qsTr("The manual is a playlist.")
        ]
    }

    KiroSlide {
        kicker: "KiroTux"
        headline: qsTr("Kiro, on Wayland.")
        lines: [
            qsTr("Five Wayland ISOs, built on Hyprland, Niri or Wayfire."),
            qsTr("Find the KiroTux ISOs on Ko-fi: ko-fi.com/erikdubois/shop")
        ]
    }

    KiroSlide {
        kicker: "Hyprland"
        headline: qsTr("Tiling with style.")
        lines: [
            qsTr("Rounded corners, blur and smooth animations, ready from the first login."),
            qsTr("Two ISOs: with DankMaterialShell or with Noctalia."),
            qsTr("Find the KiroTux ISOs on Ko-fi: ko-fi.com/erikdubois/shop")
        ]
    }

    KiroSlide {
        kicker: "Niri"
        headline: qsTr("Scroll through your windows.")
        lines: [
            qsTr("Windows open side by side on an endless strip; a new one never squeezes the others."),
            qsTr("One key shows an overview of all your workspaces."),
            qsTr("Two ISOs: with DankMaterialShell or with Noctalia."),
            qsTr("Find the KiroTux ISOs on Ko-fi: ko-fi.com/erikdubois/shop")
        ]
    }

    KiroSlide {
        kicker: "Wayfire"
        headline: qsTr("Desktop effects that wow.")
        lines: [
            qsTr("A 3D cube, wobbly windows and blur, all built in."),
            qsTr("Light on resources, with waybar and mako."),
            qsTr("Find the KiroTux ISOs on Ko-fi: ko-fi.com/erikdubois/shop")
        ]
    }

    KiroSlide {
        kicker: qsTr("KiroTux Premium settings app")
        headline: qsTr("Your desktop, set up in one window.")
        lines: [
            qsTr("Theme, icons, cursor and wallpaper. No config files."),
            qsTr("One for each window manager: Hyprland, Niri and Wayfire."),
            qsTr("Find the KiroTux ISOs on Ko-fi: ko-fi.com/erikdubois/shop")
        ]
    }

    KiroTitleSlide {
        wordmark: qsTr("Enjoy Kiro")
        tagline: qsTr("Sit back — your new system is being installed.")
    }

    function onActivate() {
        presentation.currentSlide = 0;
    }

    function onLeave() {
    }
}
