import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import theme
import components

Item {
    id: page

    property string loginError: ""

    Component.onCompleted: {
        authBridge.loginError.connect(function (message) {
            page.loginError = message
        })
        authBridge.loginSuccess.connect(function () {
            page.loginError = ""
            window.currentPage = 1
        })
    }

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 80, 460)
        spacing: Theme.spacing

        Label {
            Layout.alignment: Qt.AlignHCenter
            text: "Bienvenido"
            color: Colors.text
            font.pixelSize: Theme.fontSizeTitle
            font.bold: true
        }

        Label {
            Layout.alignment: Qt.AlignHCenter
            text: "Inicia sesión con Microsoft o entra en modo offline."
            color: Colors.mutedText
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        BMCard {
            Layout.fillWidth: true
            implicitHeight: loginLayout.implicitHeight + Theme.spacing * 2

            ColumnLayout {
                id: loginLayout
                anchors.fill: parent
                anchors.margins: Theme.spacing
                spacing: Theme.spacing

                Label {
                    text: "Modo offline"
                    color: Colors.text
                    font.pixelSize: Theme.fontSizeLg
                    font.bold: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spacingSm

                    TextField {
                        id: usernameInput
                        Layout.fillWidth: true
                        placeholderText: "Nombre de usuario"
                        color: Colors.text
                        selectionColor: Colors.primary
                        font.pixelSize: Theme.fontSize
                        background: Rectangle {
                            radius: Theme.radius
                            color: Colors.surfaceRaised
                            border.color: usernameInput.activeFocus ? Colors.primary : Colors.border
                            border.width: 1
                        }
                        onAccepted: doOfflineLogin()
                    }

                    BMButton {
                        text: "Entrar"
                        onClicked: doOfflineLogin()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 1
                    color: Colors.border
                }

                Label {
                    text: "Cuenta Microsoft"
                    color: Colors.text
                    font.pixelSize: Theme.fontSizeLg
                    font.bold: true
                }

                BMButton {
                    id: microsoftButton
                    Layout.fillWidth: true
                    text: "Iniciar sesión con Microsoft"
                    enabled: !authBridge.loginInProgress
                    contentItem: RowLayout {
                        anchors.centerIn: parent
                        spacing: 8
                        BusyIndicator {
                            visible: authBridge.loginInProgress
                            running: authBridge.loginInProgress
                            implicitWidth: 16
                            implicitHeight: 16
                        }
                        Text {
                            text: microsoftButton.text
                            color: microsoftButton.paletteText
                            font: microsoftButton.font
                        }
                    }
                    onClicked: {
                        page.loginError = ""
                        var url = authBridge.getLoginUrl()
                        if (url.length > 0) {
                            Qt.openUrlExternally(url)
                            urlDialog.open()
                        }
                    }
                }

                Label {
                    Layout.alignment: Qt.AlignHCenter
                    text: page.loginError
                    color: Colors.danger
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                    visible: page.loginError.length > 0
                }
            }
        }
    }

    Dialog {
        id: urlDialog
        anchors.centerIn: parent
        title: "URL de autorización"
        modal: true
        padding: Theme.spacing
        width: Math.min(parent.width - 80, 480)

        standardButtons: Dialog.Cancel | Dialog.Ok
        onAccepted: {
            var url = urlInput.text.trim()
            if (url.length > 0) {
                authBridge.completeMicrosoftLogin(url)
            }
        }

        contentItem: ColumnLayout {
            spacing: Theme.spacing
            Label {
                text: "Pega la URL de autorización que Microsoft te mostró."
                color: Colors.mutedText
                wrapMode: Text.WordWrap
            }
            TextField {
                id: urlInput
                Layout.fillWidth: true
                placeholderText: "https://login.live.com/oauth20_desktop.htm?..."
                color: Colors.text
                font.pixelSize: Theme.fontSize
                background: Rectangle {
                    radius: Theme.radius
                    color: Colors.surfaceRaised
                    border.color: urlInput.activeFocus ? Colors.primary : Colors.border
                    border.width: 1
                }
            }
        }
    }

    function doOfflineLogin() {
        var name = usernameInput.text.trim()
        if (name.length === 0) return
        page.loginError = ""
        authBridge.loginOffline(name)
    }
}
