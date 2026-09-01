import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window

    width: 1180
    height: 720
    minimumWidth: 900
    minimumHeight: 560
    visible: true
    title: "BM-MCL"
    color: theme.background

    QtObject {
        id: theme

        readonly property color background: "#111827"
        readonly property color surface: "#1f2937"
        readonly property color surfaceRaised: "#273449"
        readonly property color primary: "#3b82f6"
        readonly property color primaryHover: "#60a5fa"
        readonly property color text: "#f9fafb"
        readonly property color mutedText: "#9ca3af"
        readonly property color border: "#374151"
        readonly property int spacing: 16
        readonly property int radius: 10
    }

    property int currentPage: 0

    component NavigationButton: Button {
        required property int pageIndex
        required property string label
        required property string iconText

        Layout.fillWidth: true
        implicitHeight: 46
        text: iconText + "  " + label
        horizontalAlignment: Text.AlignLeft
        font.pixelSize: 14
        font.weight: Font.Medium

        background: Rectangle {
            radius: theme.radius
            color: parent.down
                ? Qt.darker(theme.primary, 1.15)
                : parent.hovered || currentPage === pageIndex
                    ? theme.primary
                    : "transparent"
        }

        contentItem: Text {
            text: parent.text
            color: theme.text
            font: parent.font
            horizontalAlignment: parent.horizontalAlignment
            verticalAlignment: Text.AlignVCenter
            leftPadding: 14
            elide: Text.ElideRight
        }

        onClicked: currentPage = pageIndex
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            id: sidebar

            Layout.fillHeight: true
            Layout.preferredWidth: 236
            color: theme.surface

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: theme.spacing
                spacing: 8

                Label {
                    text: "BM-MCL"
                    color: theme.text
                    font.pixelSize: 25
                    font.bold: true
                }

                Label {
                    text: "Minecraft Launcher"
                    color: theme.mutedText
                    font.pixelSize: 12
                    bottomPadding: 20
                }

                NavigationButton {
                    pageIndex: 0
                    label: "Inicio"
                    iconText: "⌂"
                }

                NavigationButton {
                    pageIndex: 1
                    label: "Versiones"
                    iconText: "◇"
                }

                NavigationButton {
                    pageIndex: 2
                    label: "Ajustes"
                    iconText: "⚙"
                }

                Item {
                    Layout.fillHeight: true
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 1
                    color: theme.border
                }

                Label {
                    text: "v0.1.0"
                    color: theme.mutedText
                    font.pixelSize: 12
                    topPadding: 8
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: currentPage

            Item {
                id: homePage

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 40
                    spacing: 20

                    Label {
                        text: "Bienvenido a BM-MCL"
                        color: theme.text
                        font.pixelSize: 32
                        font.bold: true
                    }

                    Label {
                        text: "Selecciona una versión para preparar tu próxima partida."
                        color: theme.mutedText
                        font.pixelSize: 16
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 200
                        radius: theme.radius
                        color: theme.surface
                        border.color: theme.border

                        ColumnLayout {
                            anchors.centerIn: parent
                            spacing: 12

                            Label {
                                Layout.alignment: Qt.AlignHCenter
                                text: "Aún no hay una versión seleccionada"
                                color: theme.text
                                font.pixelSize: 18
                                font.bold: true
                            }

                            Button {
                                Layout.alignment: Qt.AlignHCenter
                                text: "Explorar versiones"
                                onClicked: currentPage = 1

                                background: Rectangle {
                                    radius: theme.radius
                                    color: parent.down ? Qt.darker(theme.primary, 1.15) : parent.hovered ? theme.primaryHover : theme.primary
                                }

                                contentItem: Text {
                                    text: parent.text
                                    color: theme.text
                                    font: parent.font
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    leftPadding: 16
                                    rightPadding: 16
                                }
                            }
                        }
                    }

                    Item {
                        Layout.fillHeight: true
                    }
                }
            }

            Item {
                id: versionsPage

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 40
                    spacing: 20

                    Label {
                        text: "Versiones"
                        color: theme.text
                        font.pixelSize: 32
                        font.bold: true
                    }

                    Label {
                        text: "Las versiones disponibles aparecerán aquí al conectar esta vista con versionBridge."
                        color: theme.mutedText
                        font.pixelSize: 16
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: theme.radius
                        color: theme.surface
                        border.color: theme.border

                        Label {
                            anchors.centerIn: parent
                            text: "Catálogo de versiones pendiente de cargar"
                            color: theme.mutedText
                            font.pixelSize: 15
                        }
                    }
                }
            }

            Item {
                id: settingsPage

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 40
                    spacing: 20

                    Label {
                        text: "Ajustes"
                        color: theme.text
                        font.pixelSize: 32
                        font.bold: true
                    }

                    Label {
                        text: "Configura la instalación, tu cuenta y las preferencias del lanzador."
                        color: theme.mutedText
                        font.pixelSize: 16
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 136
                        radius: theme.radius
                        color: theme.surface
                        border.color: theme.border

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: theme.spacing
                            spacing: 6

                            Label {
                                text: "Próximo paso"
                                color: theme.text
                                font.pixelSize: 16
                                font.bold: true
                            }

                            Label {
                                text: "Conectar los controles con settingsBridge para mostrar y guardar la configuración."
                                color: theme.mutedText
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                    }

                    Item {
                        Layout.fillHeight: true
                    }
                }
            }
        }
    }
}
