import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import components

Item {
    id: page

    property var versions: []
    property string statusText: ""
    property string installError: ""
    property int progressValue: 0
    property int progressMax: 1

    function reload() {
        page.versions = versionBridge.getVersions(snapshotsCheck.checked)
    }

    Component.onCompleted: {
        page.reload()
        versionBridge.versionsChanged.connect(function (list) {
            page.versions = list
        })
        versionBridge.progress.connect(function (current, maximum) {
            page.progressValue = current
            page.progressMax = Math.max(maximum, 1)
        })
        versionBridge.statusChanged.connect(function (status) {
            page.statusText = status
        })
        versionBridge.installError.connect(function (message) {
            page.installError = message
        })
        versionBridge.installFinished.connect(function (versionId) {
            page.installError = ""
            page.reload()
        })
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.pageMargin
        spacing: Theme.spacingLg

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing
            Label {
                text: "Versiones"
                color: Colors.text
                font.pixelSize: Theme.fontSizeTitle
                font.bold: true
            }
            Item { Layout.fillWidth: true }
            BMButton {
                text: "Actualizar lista"
                paletteBase: Colors.surfaceRaised
                paletteHover: Colors.border
                palettePressed: Colors.border
                enabled: !versionBridge.isInstalling
                onClicked: page.reload()
            }
        }

        BMCard {
            Layout.fillWidth: true
            implicitHeight: filterLayout.implicitHeight + Theme.spacing * 2

            ColumnLayout {
                id: filterLayout
                anchors.fill: parent
                anchors.margins: Theme.spacing
                spacing: Theme.spacingSm

                CheckBox {

                    id: snapshotsCheck

                    text: "Mostrar snapshots"

                    palette { buttonText: Colors.text }

                    font.pixelSize: Theme.fontSize

                    onToggled: page.reload()

                }

                Label {
                    text: "Desmarca para ver solo versiones estables."
                    color: Colors.mutedText
                    font.pixelSize: Theme.fontSizeSm
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spacingSm
            visible: versionBridge.isInstalling

            BMProgressBar {
                Layout.fillWidth: true
                value: (page.progressMax > 0) ? page.progressValue / page.progressMax : 0
            }

            Label {
                text: (page.statusText.length > 0) ? page.statusText : "Instalando…"
                color: Colors.mutedText
                font.pixelSize: Theme.fontSize
            }
        }

        BMCard {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Flickable {
                id: versionScroll

                anchors.fill: parent

                clip: true

                contentWidth: width
                contentHeight: versionList.contentHeight

                boundsBehavior: Flickable.StopAtBounds

                ListView {
                    id: versionList
                    clip: true
                    width: versionScroll.width
                    model: page.versions
                    spacing: 8

                    delegate: Rectangle {
                        width: versionList.width
                        height: 56
                        radius: Theme.radius
                        color: Colors.surfaceRaised
                        border.color: Colors.border
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            spacing: Theme.spacingSm

                            Label {
                                text: modelData.id
                                color: Colors.text
                                font.pixelSize: Theme.fontSizeLg
                                font.bold: true
                            }

                            Label {
                                text: modelData.type
                                color: Colors.mutedText
                                font.pixelSize: Theme.fontSizeSm
                            }

                            Label {
                                text: (modelData.installed === true) ? "Instalada" : "Sin instalar"
                                color: (modelData.installed === true) ? Colors.success : Colors.mutedText
                                font.pixelSize: Theme.fontSizeSm
                            }

                            Item { Layout.fillWidth: true }

                            BMButton {
                                visible: modelData.installed !== true
                                text: "Instalar"
                                enabled: !versionBridge.isInstalling
                                onClicked: {
                                    page.installError = ""
                                    versionBridge.installVersion(modelData.id)
                                }
                            }
                        }
                    }
                }
            }
        }

        Label {
            Layout.alignment: Qt.AlignHCenter
            text: page.installError
            color: Colors.danger
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            visible: page.installError.length > 0
        }
    }
}
