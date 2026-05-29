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
        interval: 6500
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
                text: kicker.toUpperCase()
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
            "chaotic-aur enabled by default — thousands of AUR packages as pre-built binaries.",
            "yay, paru and the pamac-aur GUI built in.",
            "Erik's nemesis_repo enabled out of the box."
        ]
    }

    KiroSlide {
        kicker: "Performance"
        headline: "Tuned for speed"
        lines: [
            "Boots linux-cachyos, with linux-zen on standby.",
            "BBR, autotuned buffers, ananicy-cpp and zram — pre-applied.",
            "Kernel-agnostic: bring linux-hardened, an LTS, or your own."
        ]
    }

    KiroSlide {
        kicker: "Desktop"
        headline: "Your desktop, your way"
        lines: [
            "Xfce and Ohmychadwm ready at first login.",
            "13 desktops — 7 tilers, 6 full DEs — on demand from ATT.",
            "Themed and polished out of the box, no ricing required."
        ]
    }

    KiroSlide {
        kicker: "Security"
        headline: "Secure and resilient"
        lines: [
            "firewalld enabled by default.",
            "A sysctl hardening layer, already applied.",
            "No telemetry. Timeshift snapshots roll back a bad update in minutes."
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
