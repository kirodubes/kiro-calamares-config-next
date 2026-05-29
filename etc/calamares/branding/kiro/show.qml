/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2015 Teo Mrnjavac <teo@kde.org>
 *   SPDX-FileCopyrightText: 2018 Adriaan de Groot <groot@kde.org>
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 */

import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation
{
    id: presentation

    // Kiro brand backdrop: fills the letterbox bands around each slide
    // with the same near-black slate gradient the screenshots use, so the
    // slideshow reads as one cohesive surface instead of letterboxed images.
    Rectangle {
        anchors.fill: parent
        z: -1
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#020617" }
            GradientStop { position: 1.0; color: "#0F172A" }
        }
    }

    function nextSlide() {
        console.log("QML Component (default slideshow) Next slide");
        presentation.goToNextSlide();
    }

    Timer {
        id: advanceTimer
        interval: 5000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: nextSlide()
    }

    Slide {
        anchors.fill: parent
        anchors.verticalCenterOffset: 0
        Image {
            id: background1
            source: "01cal.jpg"
            width: parent.width; height: parent.height
            verticalAlignment: Image.AlignTop
            fillMode: Image.PreserveAspectFit
            anchors.fill: parent
        }

    }


    Slide {
        anchors.fill: parent
        anchors.verticalCenterOffset: 0
        Image {
            id: background5
            source: "05cal.jpg"
            width: parent.width; height: parent.height
            verticalAlignment: Image.AlignTop
            fillMode: Image.PreserveAspectFit
            anchors.fill: parent
        }

    }

    Slide {
        anchors.fill: parent
        anchors.verticalCenterOffset: 0
        Image {
            id: background6
            source: "06cal.jpg"
            width: parent.width; height: parent.height
            verticalAlignment: Image.AlignTop
            fillMode: Image.PreserveAspectFit
            anchors.fill: parent
        }

    }

    Slide {
        anchors.fill: parent
        anchors.verticalCenterOffset: 0
        Image {
            id: background7
            source: "07cal.jpg"
            width: parent.width; height: parent.height
            verticalAlignment: Image.AlignTop
            fillMode: Image.PreserveAspectFit
            anchors.fill: parent
        }

    }

    Slide {
        anchors.fill: parent
        anchors.verticalCenterOffset: 0
        Image {
            id: background8
            source: "08cal.jpg"
            width: parent.width; height: parent.height
            verticalAlignment: Image.AlignTop
            fillMode: Image.PreserveAspectFit
            anchors.fill: parent
        }

    }

    Slide {
        anchors.fill: parent
        anchors.verticalCenterOffset: 0
        Image {
            id: background9
            source: "09cal.jpg"
            width: parent.width; height: parent.height
            verticalAlignment: Image.AlignTop
            fillMode: Image.PreserveAspectFit
            anchors.fill: parent
        }

    }

    Slide {
        anchors.fill: parent
        anchors.verticalCenterOffset: 0
        Image {
            id: background10
            source: "10cal.jpg"
            width: parent.width; height: parent.height
            verticalAlignment: Image.AlignTop
            fillMode: Image.PreserveAspectFit
            anchors.fill: parent
        }

    }

    Slide {
        anchors.fill: parent
        anchors.verticalCenterOffset: 0
        Image {
            id: background11
            source: "11cal.jpg"
            width: parent.width; height: parent.height
            verticalAlignment: Image.AlignTop
            fillMode: Image.PreserveAspectFit
            anchors.fill: parent
        }

    }

    Slide {
        anchors.fill: parent
        anchors.verticalCenterOffset: 0
        Image {
            id: background12
            source: "12cal.jpg"
            width: parent.width; height: parent.height
            verticalAlignment: Image.AlignTop
            fillMode: Image.PreserveAspectFit
            anchors.fill: parent
        }

    }

    function onActivate() {
          console.log("QML Component (default slideshow) activated");
          presentation.currentSlide = 0;
    }

    function onLeave() {
          console.log("QML Component (default slideshow) deactivated");
    }

}
