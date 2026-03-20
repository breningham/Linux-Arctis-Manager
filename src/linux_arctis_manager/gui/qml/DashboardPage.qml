import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    title: "Status"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Kirigami.Units.largeSpacing
        spacing: Kirigami.Units.largeSpacing * 2

        // HERO BANNER
        ColumnLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: Kirigami.Units.smallSpacing
            
            Kirigami.Icon {
                Layout.alignment: Qt.AlignHCenter
                implicitWidth: 96
                implicitHeight: 96
                source: backend.isDisconnected ? "bluetooth-disconnected" : "audio-headset"
                opacity: backend.isDisconnected || backend.isOffline ? 0.5 : 1.0
                visible: !backend.isDisconnected
            }

            Controls.Label {
                Layout.alignment: Qt.AlignHCenter
                text: backend.isDisconnected ? "Arctis Manager" : backend.deviceName
                font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.5
                font.bold: true
            }

            Controls.Label {
                Layout.alignment: Qt.AlignHCenter
                text: backend.isDisconnected ? "No supported device found" : (backend.isOffline ? "Offline" : (backend.deviceStatus.isCharging ? "Charging (Offline)" : "Connected and Active"))
                color: Kirigami.Theme.disabledTextColor
                visible: true
            }
        }

        // CARDS
        Kirigami.Card {
            Layout.fillWidth: true
            visible: !backend.isOffline && !backend.isDisconnected
            
            header: Controls.Label {
                text: "Device Status"
                font.bold: true
                padding: Kirigami.Units.largeSpacing
            }

            contentItem: ColumnLayout {
                spacing: Kirigami.Units.largeSpacing

                Kirigami.FormLayout {
                    Layout.fillWidth: true
                    
                    // Battery
                    Controls.ProgressBar {
                        Kirigami.FormData.label: "Battery"
                        Layout.fillWidth: true
                        from: 0
                        to: 100
                        value: backend.deviceStatus.batteryLevel || 0
                        visible: backend.deviceStatus.hasBattery
                        
                        contentItem: Item {
                            implicitWidth: 200
                            implicitHeight: 18
                            Rectangle {
                                width: parent.width
                                height: parent.height
                                radius: height / 2
                                color: Kirigami.Theme.alternateBackgroundColor
                            }
                            Rectangle {
                                width: Math.max(parent.width * (parent.parent.value / 100), radius*2)
                                height: parent.height
                                radius: height / 2
                                color: parent.parent.value > 20 ? Kirigami.Theme.positiveTextColor : Kirigami.Theme.negativeTextColor
                            }
                            Controls.Label {
                                anchors.centerIn: parent
                                text: (backend.deviceStatus.batteryLevel || 0) + "%" + (backend.deviceStatus.isCharging ? " ⚡" : "")
                                color: Kirigami.Theme.textColor
                                font.bold: true
                            }
                        }
                    }

                    // Bluetooth
                    Controls.Label {
                        Kirigami.FormData.label: "Bluetooth"
                        text: backend.deviceStatus.bluetoothConnected ? "Connected" : "Disconnected"
                        color: backend.deviceStatus.bluetoothConnected ? Kirigami.Theme.positiveTextColor : Kirigami.Theme.negativeTextColor
                        visible: backend.deviceStatus.hasBluetooth
                        font.bold: true
                    }

                    // Microphone
                    Controls.Label {
                        Kirigami.FormData.label: "Microphone"
                        text: backend.deviceStatus.micMuted ? "Muted" : "Active"
                        color: backend.deviceStatus.micMuted ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.positiveTextColor
                        visible: backend.deviceStatus.hasMic
                        font.bold: true
                    }
                }
                
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: backend.deviceStatus.hasMix
                    spacing: Kirigami.Units.smallSpacing
                    
                    Kirigami.Separator { Layout.fillWidth: true }
                    
                    Controls.Label {
                        text: "Audio Mix"
                        font.bold: true
                        Layout.topMargin: Kirigami.Units.smallSpacing
                    }
                    
                    RowLayout {
                        Layout.fillWidth: true
                        Kirigami.Icon { source: "input-gaming"; implicitWidth: 24; implicitHeight: 24; color: Kirigami.Theme.disabledTextColor }
                        Controls.Slider {
                            Layout.fillWidth: true
                            from: 0
                            to: 100
                            value: {
                                let total = backend.deviceStatus.mixChat + backend.deviceStatus.mixMedia;
                                return total === 0 ? 50 : (backend.deviceStatus.mixChat / total) * 100.0;
                            }
                            enabled: false // Read only
                        }
                        Kirigami.Icon { source: "audio-headset"; implicitWidth: 24; implicitHeight: 24; color: Kirigami.Theme.disabledTextColor }
                    }
                }
            }
        }

        Item { Layout.fillHeight: true } // spacer
    }
}
