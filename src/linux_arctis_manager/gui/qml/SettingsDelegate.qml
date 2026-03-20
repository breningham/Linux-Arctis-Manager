import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

ColumnLayout {
    Layout.fillWidth: true
    spacing: Kirigami.Units.smallSpacing

    RowLayout {
        Layout.fillWidth: true
        spacing: Kirigami.Units.largeSpacing

        Controls.Label {
            text: modelData.title
            Layout.fillWidth: true
            elide: Text.ElideRight
            font.bold: true
            font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.1
        }

        Loader {
            sourceComponent: {
                if (modelData.type === "slider") return sliderComp;
                if (modelData.type === "toggle") return toggleComp;
                if (modelData.type === "discrete_map" || modelData.type === "select") return comboComp;
                return defaultComp;
            }
            Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
        }
    }

    Controls.Label {
        Layout.fillWidth: true
        text: modelData.description
        color: Kirigami.Theme.disabledTextColor
        font.pointSize: Kirigami.Theme.smallFont.pointSize
        wrapMode: Text.WordWrap
        visible: text !== ""
    }

    Component {
        id: sliderComp
        RowLayout {
            Controls.Slider {
                id: ctrlSlider
                Layout.preferredWidth: 200
                from: modelData.min
                to: modelData.max
                stepSize: modelData.step
                value: modelData.value
                onMoved: {
                    backend.changeSetting(modelData.id, value)
                }
            }
            Controls.Label {
                text: ctrlSlider.value
                Layout.minimumWidth: Kirigami.Units.gridUnit * 2
                horizontalAlignment: Text.AlignRight
            }
        }
    }

    Component {
        id: toggleComp
        Controls.Switch {
            checked: modelData.value
            onToggled: backend.changeSetting(modelData.id, checked)
        }
    }

    Component {
        id: comboComp
        Controls.ComboBox {
            Layout.preferredWidth: 250
            Layout.maximumWidth: 350
            
            textRole: "label"
            valueRole: "value"
            model: modelData.options
            
            Component.onCompleted: {
                for (let i = 0; i < count; i++) {
                    if (model.get ? (model.get(i).value === modelData.value) : (model[i].value === modelData.value)) {
                        currentIndex = i;
                        break;
                    }
                }
            }
            
            onActivated: {
                let val = model.get ? model.get(currentIndex).value : model[currentIndex].value;
                backend.changeSetting(modelData.id, val);
            }
        }
    }
    
    Component {
        id: defaultComp
        Controls.Label { text: "Unsupported setting type: " + modelData.type }
    }
}
