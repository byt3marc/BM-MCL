import QtQuick

import QtQuick.Controls

import QtQuick.Layouts

import theme
import pages

ApplicationWindow {
    id: window

    width: 1180
    height: 720
    minimumWidth: 900
    minimumHeight: 560
    visible: true
    title: "BM-MCL"
    color: Colors.background

    property int currentPage: 0

    readonly property bool hasAccount: authBridge.selectedAccount && authBridge.selectedAccount.uuid !== ""

    // Fuerza Login cuando no hay cuenta activa
    function ensureValidPage() {
        if (!window.hasAccount && window.currentPage !== 0) {
            window.currentPage = 0
        }
    }

    Component.onCompleted: {
        ensureValidPage()
        authBridge.selectedAccountChanged.connect(function () {
            if (window.hasAccount) {
                if (window.currentPage === 0) window.currentPage = 1
            }
            ensureValidPage()
        })
    }

    component NavigationButton: Button {
        required property int pageIndex
        required property string label
        required property string iconText

        Layout.fillWidth: true
        implicitHeight: 46
        text: iconText + "  " + label
        font.pixelSize: Theme.fontSize
        font.weight: Font.Medium

        background: Rectangle {
            radius: Theme.radius
            color: parent.down
                ? Colors.primaryPressed
                : parent.hovered || window.currentPage === pageIndex
                    ? Colors.primary
                    : "transparent"
        }

        contentItem: Text {
            text: parent.text
            color: Colors.text
            font: parent.font
            horizontalAlignment: parent.horizontalAlignment
            verticalAlignment: Text.AlignVCenter
            leftPadding: 14
            elide: Text.ElideRight
        }

        onClicked: window.currentPage = pageIndex
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            id: sidebar

            Layout.fillHeight: true
            Layout.preferredWidth: Theme.sidebarWidth
            color: Colors.surface
            visible: window.hasAccount
            width: window.hasAccount ? Theme.sidebarWidth : 0

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.spacing
                spacing: 8

                Label {
                    text: "BM-MCL"
                    color: Colors.text
                    font.pixelSize: 26
                    font.bold: true
                }

                Label {
                    text: "Minecraft Launcher"
                    color: Colors.mutedText
                    font.pixelSize: Theme.fontSizeSm
                    bottomPadding: 20
                }

                NavigationButton {
                    pageIndex: 1
                    label: "Inicio"
                    iconText: "⌂"
                }

                NavigationButton {
                    pageIndex: 2
                    label: "Versiones"
                    iconText: "◇"
                }

                NavigationButton {
                    pageIndex: 3
                    label: "Ajustes"
                    iconText: "⚙"
                }

                Item {
                    Layout.fillHeight: true
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 1
                    color: Colors.border
                }

                Label {
                    text: "v0.1.0"
                    color: Colors.mutedText
                    font.pixelSize: Theme.fontSizeSm
                    topPadding: 8
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: window.currentPage

            // 0 — Login
            Login {}

            // 1 — Home
            Home {}

            // 2 — Library (Versiones)
            Library {}

            // 3 — Settings
            Settings {}
        }
    }
}
