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

        Kirigami.FormLayout {
            Layout.fillWidth: true

            Kirigami.Separator { Kirigami.FormData.isSection: true; Kirigami.FormData.label: "General" }
            Repeater {
                model: backend.generalSettings
                delegate: SettingsDelegate {}
            }
            
            Kirigami.Separator { 
                Kirigami.FormData.isSection: true; 
                Kirigami.FormData.label: "Device"; 
                visible: !backend.isOffline && backend.deviceSettings.length > 0 
            }
            Repeater {
                model: backend.deviceSettings
                delegate: SettingsDelegate {}
            }
        }
        
        Item { Layout.fillHeight: true } // Spacer
    }
}
