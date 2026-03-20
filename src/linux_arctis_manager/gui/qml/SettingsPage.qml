import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    title: "Settings"
    leftPadding: Kirigami.Units.largeSpacing
    rightPadding: Kirigami.Units.largeSpacing
    topPadding: Kirigami.Units.largeSpacing
    bottomPadding: Kirigami.Units.largeSpacing

    ColumnLayout {
        width: parent.width
        spacing: Kirigami.Units.largeSpacing

        Kirigami.Card {
            Layout.fillWidth: true
            header: Controls.Label {
                text: "General"
                font.bold: true
                padding: Kirigami.Units.largeSpacing
            }
            contentItem: Item {
                implicitHeight: genCol.implicitHeight + (Kirigami.Units.largeSpacing * 2)
                ColumnLayout {
                    id: genCol
                    anchors.fill: parent
                    anchors.margins: Kirigami.Units.largeSpacing
                    spacing: Kirigami.Units.largeSpacing * 1.5
                    Repeater {
                        model: backend.generalSettings
                        delegate: SettingsDelegate {}
                    }
                }
            }
        }

        Kirigami.Card {
            Layout.fillWidth: true
            visible: !backend.isOffline && backend.deviceSettings.length > 0
            header: Controls.Label {
                text: "Device"
                font.bold: true
                padding: Kirigami.Units.largeSpacing
            }
            contentItem: Item {
                implicitHeight: devCol.implicitHeight + (Kirigami.Units.largeSpacing * 2)
                ColumnLayout {
                    id: devCol
                    anchors.fill: parent
                    anchors.margins: Kirigami.Units.largeSpacing
                    spacing: Kirigami.Units.largeSpacing * 1.5
                    Repeater {
                        model: backend.deviceSettings
                        delegate: SettingsDelegate {}
                    }
                }
            }
        }
        
        Item { Layout.fillHeight: true; Layout.minimumHeight: Kirigami.Units.largeSpacing * 2 } // Spacer
    }
}
