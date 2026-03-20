import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root
    width: 650
    height: 800
    visible: true
    title: backend.deviceName !== "" ? backend.deviceName : "Arctis Manager"

    globalDrawer: Kirigami.GlobalDrawer {
        isMenu: false
        actions: [
            Kirigami.Action {
                text: "Status"
                icon.name: "audio-card"
                onTriggered: pageStack.replace(dashboardComponent)
            },
            Kirigami.Action {
                text: "Settings"
                icon.name: "preferences-system"
                onTriggered: pageStack.replace(settingsComponent)
            }
        ]
    }

    Component { id: dashboardComponent; DashboardPage {} }
    Component { id: settingsComponent; SettingsPage {} }

    pageStack.initialPage: dashboardComponent
}
