import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Item {
    implicitWidth: parent ? parent.width : 400
    implicitHeight: layout.implicitHeight
    Kirigami.FormData.label: modelData.title

    ColumnLayout {
        id: layout
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: Kirigami.Units.smallSpacing

        Loader {
            Layout.fillWidth: true
            sourceComponent: {
                if (modelData.type === "slider") return sliderComp;
                if (modelData.type === "toggle") return toggleComp;
                if (modelData.type === "discrete_map" || modelData.type === "select") return comboComp;
                return defaultComp;
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
    }

    Component {
        id: sliderComp
        RowLayout {
            Controls.Slider {
                Layout.fillWidth: true
                from: modelData.min
                to: modelData.max
                stepSize: modelData.step
                value: modelData.value
                onMoved: {
                    backend.changeSetting(modelData.id, value)
                }
            }
            Controls.Label {
                text: parent.children[0].value
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
            Layout.fillWidth: true
            textRole: "label"
            valueRole: "value"
            model: modelData.options
            
            // Set current index based on value
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
