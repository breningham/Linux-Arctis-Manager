import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    title: "Settings"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Kirigami.Units.largeSpacing
        spacing: Kirigami.Units.largeSpacing

        Kirigami.Card {
            Layout.fillWidth: true
            header: Controls.Label {
                text: "General"
                font.bold: true
                padding: Kirigami.Units.largeSpacing
            }
            contentItem: Kirigami.FormLayout {
                Repeater {
                    model: backend.generalSettings
                    delegate: SettingsDelegate {}
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
            contentItem: Kirigami.FormLayout {
                Repeater {
                    model: backend.deviceSettings
                    delegate: SettingsDelegate {}
                }
            }
        }
        
        Item { Layout.fillHeight: true } // Spacer
    }
}
