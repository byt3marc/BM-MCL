import QtQuick
import theme

Rectangle {
    id: root

    property color paletteBackground: Colors.surface
    property color paletteBorder: Colors.border

    radius: Theme.radiusLg
    color: paletteBackground
    border.color: paletteBorder
}
