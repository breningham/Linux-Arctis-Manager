import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root
    width: 900
    height: 650
    visible: true
    title: backend.deviceName !== "" ? backend.deviceName : "Arctis Manager"

    // Using a standard SplitView for reliable desktop-style sidebar navigation
    // This avoids the "cog wheel" GlobalDrawer mobile behavior completely
    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 200
            Layout.fillHeight: true
            color: Kirigami.Theme.alternateBackgroundColor

            ListView {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.smallSpacing
                model: ListModel {
                    ListElement { text: "Status"; icon: "audio-card"; page: "dashboard" }
                    ListElement { text: "Settings"; icon: "preferences-system"; page: "settings" }
                }
                delegate: Kirigami.BasicListItem {
                    text: model.text
                    icon: model.icon
                    highlighted: ListView.isCurrentItem
                    onClicked: {
                        ListView.view.currentIndex = index
                        if (model.page === "dashboard") {
                            mainLoader.sourceComponent = dashboardComponent
                        } else {
                            mainLoader.sourceComponent = settingsComponent
                        }
                    }
                }
            }
            
            // Right border line
            Rectangle {
                width: 1
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                color: Kirigami.Theme.disabledTextColor
                opacity: 0.3
            }
        }

        Loader {
            id: mainLoader
            Layout.fillWidth: true
            Layout.fillHeight: true
            sourceComponent: dashboardComponent
        }
    }

    Component { id: dashboardComponent; DashboardPage {} }
    Component { id: settingsComponent; SettingsPage {} }
}
