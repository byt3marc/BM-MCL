import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import components

Item {
    id: page

    property string settingsError: ""
    property string savedMessage: ""

    function syncFromBridge() {
        installDirInput.text = settingsBridge.installDir || ""
        ramMinInput.value = settingsBridge.ramMin
        ramMaxInput.value = settingsBridge.ramMax
        javaPathInput.text = settingsBridge.javaPath || ""
        showSnapshotsCheck.checked = settingsBridge.showSnapshots
        keepLauncherOpenCheck.checked = settingsBridge.keepLauncherOpen
        themeSelector.currentIndex = (settingsBridge.theme === "light") ? 1 : 0
        concurrentDownloadsInput.value = settingsBridge.concurrentDownloads
    }

    function buildPayload() {
        return {
            "install_dir": installDirInput.text.trim(),
            "ram_min_mb": Math.floor(ramMinInput.value),
            "ram_max_mb": Math.floor(ramMaxInput.value),
            "java_path": javaPathInput.text.trim(),
            "show_snapshots": showSnapshotsCheck.checked,
            "keep_launcher_open": keepLauncherOpenCheck.checked,
            "theme": (themeSelector.currentIndex === 1 ? "light" : "dark"),
            "concurrent_downloads": Math.floor(concurrentDownloadsInput.value)
        }
    }

    Component.onCompleted: {
        syncFromBridge()
        settingsBridge.settingsError.connect(function (message) {
            page.settingsError = message
        })
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.pageMargin
        spacing: Theme.spacingLg

        Label {
            text: "Ajustes"
            color: Colors.text
            font.pixelSize: Theme.fontSizeTitle
            font.bold: true
        }

        Label {
            text: "Configura la instalación, el rendimiento y la apariencia del lanzador."
            color: Colors.mutedText
            font.pixelSize: Theme.fontSizeLg
        }

        BMCard {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ScrollView {
                anchors.fill: parent
                clip: true

                ColumnLayout {
                    id: settingsForm
                    width: parent.width
                    spacing: Theme.spacingLg

                    BMCard {
                        Layout.fillWidth: true
                        implicitHeight: installLayout.implicitHeight + Theme.spacing * 2

                        ColumnLayout {
                            id: installLayout
                            anchors.fill: parent
                            anchors.margins: Theme.spacing
                            spacing: Theme.spacingSm

                            Label {
                                text: "Instalación"
                                color: Colors.text
                                font.pixelSize: Theme.fontSizeLg
                                font.bold: true
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.spacing
                                Label {
                                    text: "Carpeta"
                                    color: Colors.mutedText
                                    font.pixelSize: Theme.fontSize
                                    Layout.preferredWidth: 120
                                }
                                TextField {
                                    id: installDirInput
                                    Layout.fillWidth: true
                                    color: Colors.text
                                    placeholderText: "/ruta/al/minecraft"
                                    font.pixelSize: Theme.fontSize
                                    background: Rectangle {
                                        radius: Theme.radius
                                        color: Colors.surfaceRaised
                                        border.color: installDirInput.activeFocus ? Colors.primary : Colors.border
                                        border.width: 1
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.spacing
                                Label {
                                    text: "Java"
                                    color: Colors.mutedText
                                    font.pixelSize: Theme.fontSize
                                    Layout.preferredWidth: 120
                                }
                                TextField {
                                    id: javaPathInput
                                    Layout.fillWidth: true
                                    color: Colors.text
                                    placeholderText: "Opcional: ruta a java"
                                    font.pixelSize: Theme.fontSize
                                    background: Rectangle {
                                        radius: Theme.radius
                                        color: Colors.surfaceRaised
                                        border.color: javaPathInput.activeFocus ? Colors.primary : Colors.border
                                        border.width: 1
                                    }
                                }
                            }
                        }
                    }

                    BMCard {
                        Layout.fillWidth: true
                        implicitHeight: perfLayout.implicitHeight + Theme.spacing * 2

                        ColumnLayout {
                            id: perfLayout
                            anchors.fill: parent
                            anchors.margins: Theme.spacing
                            spacing: Theme.spacingSm

                            Label {
                                text: "Rendimiento"
                                color: Colors.text
                                font.pixelSize: Theme.fontSizeLg
                                font.bold: true
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.spacing
                                Label {
                                    text: "RAM mínima (MB)"
                                    color: Colors.mutedText
                                    font.pixelSize: Theme.fontSize
                                    Layout.preferredWidth: 120
                                }
                                SpinBox {

                                    id: ramMinInput

                                    Layout.fillWidth: true

                                    from: 512

                                    to: 32768

                                    stepSize: 512

                                    value: 2048

                                    palette { buttonText: Colors.text }

                                    font.pixelSize: Theme.fontSize

                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.spacing
                                Label {
                                    text: "RAM máxima (MB)"
                                    color: Colors.mutedText
                                    font.pixelSize: Theme.fontSize
                                    Layout.preferredWidth: 120
                                }
                                SpinBox {

                                    id: ramMaxInput

                                    Layout.fillWidth: true

                                    from: 512

                                    to: 32768

                                    stepSize: 512

                                    value: 4096

                                    palette { buttonText: Colors.text }

                                    font.pixelSize: Theme.fontSize

                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.spacing
                                Label {
                                    text: "Descargas simultáneas"
                                    color: Colors.mutedText
                                    font.pixelSize: Theme.fontSize
                                    Layout.preferredWidth: 120
                                }
                                SpinBox {

                                    id: concurrentDownloadsInput

                                    Layout.fillWidth: true

                                    from: 1

                                    to: 16

                                    stepSize: 1

                                    value: 4

                                    palette { buttonText: Colors.text }

                                    font.pixelSize: Theme.fontSize

                                }
                            }
                        }
                    }

                    BMCard {
                        Layout.fillWidth: true
                        implicitHeight: generalLayout.implicitHeight + Theme.spacing * 2

                        ColumnLayout {
                            id: generalLayout
                            anchors.fill: parent
                            anchors.margins: Theme.spacing
                            spacing: Theme.spacingSm

                            Label {
                                text: "General"
                                color: Colors.text
                                font.pixelSize: Theme.fontSizeLg
                                font.bold: true
                            }

                            CheckBox {

                                id: showSnapshotsCheck

                                text: "Mostrar snapshots"

                                palette { buttonText: Colors.text }

                                font.pixelSize: Theme.fontSize

                            }

                            CheckBox {

                                id: keepLauncherOpenCheck

                                text: "Mantener el lanzador abierto al jugar"

                                palette { buttonText: Colors.text }

                                font.pixelSize: Theme.fontSize

                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.spacing
                                Label {
                                    text: "Tema"
                                    color: Colors.mutedText
                                    font.pixelSize: Theme.fontSize
                                    Layout.preferredWidth: 120
                                }
                                ComboBox {

                                    id: themeSelector

                                    Layout.fillWidth: true

                                    model: ["Oscuro", "Claro"]

                                    currentIndex: 0

                                    palette { buttonText: Colors.text }

                                    font.pixelSize: Theme.fontSize
                                    background: Rectangle {
                                        radius: Theme.radius
                                        color: Colors.surfaceRaised
                                        border.color: themeSelector.activeFocus ? Colors.primary : Colors.border
                                        border.width: 1
                                    }
                                    contentItem: Text {

                                        text: themeSelector.currentText

                                        color: Colors.text

                                        font: themeSelector.font
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
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                        implicitHeight: 1
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingSm

                        BMButton {
                            text: "Guardar"
                            onClicked: {
                                page.settingsError = ""
                                page.savedMessage = ""
                                var ok = settingsBridge.update(page.buildPayload())
                                if (ok) {
                                    page.savedMessage = "Ajustes guardados correctamente."
                                } else {
                                    page.settingsError = "No se pudieron guardar los ajustes."
                                }
                            }
                        }

                        BMButton {
                            text: "Restablecer"
                            paletteBase: Colors.surfaceRaised
                            paletteHover: Colors.border
                            palettePressed: Colors.border
                            onClicked: {
                                var data = settingsBridge.resetToDefaults()
                                page.settingsError = ""
                                if (data && Object.keys(data).length > 0) {
                                    page.syncFromBridge()
                                    page.savedMessage = "Ajustes restablecidos a valores por defecto."
                                }
                            }
                        }

                        Item { Layout.fillWidth: true }
                    }

                    Label {
                        text: page.savedMessage
                        color: Colors.success
                        font.pixelSize: Theme.fontSize
                        visible: page.savedMessage.length > 0
                    }

                    Label {
                        text: page.settingsError
                        color: Colors.danger
                        font.pixelSize: Theme.fontSize
                        wrapMode: Text.WordWrap
                        visible: page.settingsError.length > 0
                    }
                }
            }
        }
    }
}
