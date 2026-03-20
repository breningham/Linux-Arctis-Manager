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
            font.pointSize: Math.round(Kirigami.Theme.defaultFont.pointSize * 1.1)
        }

        Loader {
            Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
            sourceComponent: {
                if (modelData.id === "pm_shutdown") return spinComp;
                if (modelData.type === "slider") return sliderComp;
                if (modelData.type === "toggle") return toggleComp;
                if (modelData.type === "discrete_map" || modelData.type === "select") return comboComp;
                return defaultComp;
            }
        }
    }

    Controls.Label {
        Layout.fillWidth: true
        text: modelData.description
        color: Kirigami.Theme.disabledTextColor
        font.pointSize: Kirigami.Theme.smallFont.pointSize > 0 ? Kirigami.Theme.smallFont.pointSize : Math.round(Kirigami.Theme.defaultFont.pointSize * 0.9)
        wrapMode: Text.WordWrap
        visible: text !== ""
        opacity: 0.8
    }

    Component {
        id: spinComp
        RowLayout {
            Controls.SpinBox {
                from: modelData.min !== undefined ? modelData.min : 0
                to: modelData.max !== undefined ? modelData.max : 120
                stepSize: modelData.step !== undefined ? modelData.step : 1
                value: modelData.value
                onValueModified: backend.changeSetting(modelData.id, value)
            }
            Controls.Label {
                text: "minutes"
                visible: modelData.id === "pm_shutdown"
            }
        }
    }

    Component {
        id: sliderComp
        RowLayout {
            Controls.Slider {
                id: ctrlSlider
                Layout.preferredWidth: 200
                from: modelData.min !== undefined ? modelData.min : 0
                to: modelData.max !== undefined ? modelData.max : 100
                stepSize: modelData.step !== undefined ? modelData.step : 1
                value: modelData.value
                onMoved: {
                    backend.changeSetting(modelData.id, value)
                }
            }
            Controls.Label {
                text: {
                    let v = Math.round(ctrlSlider.value);
                    if (modelData.id === "mic_volume") {
                        let mx = modelData.max > 0 ? modelData.max : 10;
                        return Math.round((v / mx) * 100) + "%";
                    }
                    return v;
                }
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
