import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import components

Item {
    id: page

    property string launchError: ""
    property var installedVersions: []

    function refreshInstalled() {
        page.installedVersions = versionBridge.getInstalledVersions()
    }

    function selectedVersion() {
        return versionSelector.currentText.length > 0 ? versionSelector.currentText : ""
    }

    Component.onCompleted: {
        page.refreshInstalled()
        versionBridge.installFinished.connect(function () {
            page.refreshInstalled()
        })
        launcherBridge.launchError.connect(function (message) {
            page.launchError = message
        })
        launcherBridge.launched.connect(function () {
            page.launchError = ""
        })
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.pageMargin
        spacing: Theme.spacingLg

        Label {
            text: "Iniciar partida"
            color: Colors.text
            font.pixelSize: Theme.fontSizeTitle
            font.bold: true
        }

        Label {
            text: "Selecciona una versión instalada para jugar."
            color: Colors.mutedText
            font.pixelSize: Theme.fontSizeLg
        }

        BMCard {
            Layout.fillWidth: true
            implicitHeight: homeLayout.implicitHeight + Theme.spacing * 2

            ColumnLayout {
                id: homeLayout
                anchors.fill: parent
                anchors.margins: Theme.spacing
                spacing: Theme.spacing

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacing
                    Label {
                        text: "Cuenta activa"
                        color: Colors.mutedText
                        font.pixelSize: Theme.fontSize
                    }
                    Item { Layout.fillWidth: true }
                    Label {
                        text: (authBridge.selectedAccount && authBridge.selectedAccount.name)
                            ? authBridge.selectedAccount.name
                            : "Sin cuenta"
                        color: (authBridge.selectedAccount && authBridge.selectedAccount.name)
                            ? Colors.text : Colors.warning
                        font.pixelSize: Theme.fontSize
                        font.weight: Font.Medium
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacing
                    Label {
                        text: "Versión"
                        color: Colors.mutedText
                        font.pixelSize: Theme.fontSize
                    }
                    ComboBox {

                        id: versionSelector

                        Layout.fillWidth: true

                        model: page.installedVersions

                        currentIndex: page.installedVersions.length > 0 ? 0 : -1

                        palette { buttonText: Colors.text }

                        font.pixelSize: Theme.fontSize

                        background: Rectangle {

                            radius: Theme.radius

                            color: Colors.surfaceRaised

                            border.color: versionSelector.activeFocus ? Colors.primary : Colors.border

                            border.width: 1

                        }

                        contentItem: Text {

                            text: (page.installedVersions.length > 0)
                                ? versionSelector.currentText

                                : "Sin versiones instaladas"
                            color: Colors.text

                            font: versionSelector.font

                            verticalAlignment: Text.AlignVCenter

                            leftPadding: 8

                        }
                        indicator: Label {
                            text: "▼"
                            color: Colors.mutedText
                            font.pixelSize: 10
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.right: parent.right
                            anchors.rightMargin: 12
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingSm

                    BMButton {
                        id: playButton
                        Layout.fillWidth: true
                        text: "Jugar"
                        iconText: "▶"
                        enabled: (page.installedVersions.length > 0)
                                  && (authBridge.selectedAccount && authBridge.selectedAccount.uuid)
                                  && !launcherBridge.isRunning
                        contentItem: RowLayout {
                            anchors.centerIn: parent
                            spacing: 8
                            BusyIndicator {
                                visible: launcherBridge.isRunning
                                running: launcherBridge.isRunning
                                implicitWidth: 16
                                implicitHeight: 16
                            }
                            Text {
                                text: playButton.text
                                color: playButton.paletteText
                                font: playButton.font
                            }
                        }
                        onClicked: {
                            page.launchError = ""
                            launcherBridge.launch(page.selectedVersion())
                        }
                    }

                    BMButton {
                        text: "Explorar versiones"
                        paletteBase: Colors.surfaceRaised
                        paletteHover: Colors.border
                        palettePressed: Colors.border
                        onClicked: window.currentPage = 2
                    }
                }

                Label {
                    Layout.alignment: Qt.AlignHCenter
                    text: page.launchError
                    color: Colors.danger
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                    visible: page.launchError.length > 0
                }
            }
        }

        Item { Layout.fillHeight: true }
    }
}
