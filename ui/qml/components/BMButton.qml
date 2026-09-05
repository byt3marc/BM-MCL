import QtQuick

import QtQuick.Controls

import QtQuick.Layouts
import theme

Button {
    id: control

    property string iconText: ""
    property color paletteBase: Colors.primary
    property color paletteHover: Colors.primaryHover
    property color palettePressed: Colors.primaryPressed
    property color paletteText: Colors.text
    property bool fullWidth: false

    Layout.fillWidth: fullWidth
    implicitHeight: Theme.controlHeight
    font.pixelSize: Theme.fontSize
    font.weight: Font.Medium

    background: Rectangle {
        radius: Theme.radius
        color: control.pressed ? control.palettePressed
             : control.hovered ? control.paletteHover
             : control.paletteBase
        opacity: control.enabled ? 1.0 : 0.4
    }

    contentItem: RowLayout {
        anchors.centerIn: parent
        spacing: 8

        Text {
            visible: control.iconText.length > 0
            text: control.iconText
            color: control.paletteText
            font: control.font
        }

        Text {
            visible: control.text.length > 0
            text: control.text
            color: control.paletteText
            font: control.font
        }
    }
}
