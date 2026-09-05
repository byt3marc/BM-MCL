import QtQuick
import QtQuick.Controls
import theme

ProgressBar {
    id: bar

    implicitHeight: 10
    from: 0
    to: 1
    value: 0
    enabled: value > 0

    background: Rectangle {
        radius: bar.height / 2
        color: Colors.surfaceRaised
    }

    contentItem: Rectangle {
        radius: bar.height / 2
        color: Colors.primary
        width: bar.position * bar.width
    }
}
