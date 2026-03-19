from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout, QWidget, QProgressBar

from linux_arctis_manager.i18n import I18n


class QStatusWidget(QWidget):
    main_layout: QVBoxLayout

    def __init__(self, parent: QWidget):
        super().__init__(parent)

        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(self.main_layout)
    
    def clean_layout(self):
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def update_status(self, new_status: dict[str, dict[str, dict[str, str|int]]]):
        if hasattr(self, 'status') and new_status == self.status:
            return

        self.status = new_status

        self.clean_layout()
        if not self.status:
            label = QLabel(I18n.get_instance().translate('ui', 'no_device_detected'))
            label.font().setBold(True)
            self.main_layout.addWidget(label)
            return

        index = 0
        for category, status_obj in self.status.items():
            if index > 0:
                line_separator = QWidget()
                line_separator.setFixedHeight(2)
                self.main_layout.addWidget(line_separator)
            index += 1

            category_label = QLabel(I18n.get_instance().translate('status', category))
            category_font = category_label.font()
            category_font.setBold(True)
            category_font.setPointSize(14)
            category_label.setFont(category_font)
            category_label.setStyleSheet("color: #aaa;")
            self.main_layout.addWidget(category_label)

            for status, status_o in status_obj.items():
                row_widget = QWidget()
                row_layout = QHBoxLayout()
                row_layout.setContentsMargins(10, 2, 10, 2)
                row_widget.setLayout(row_layout)
                
                status_name = I18n.translate('status', status)
                name_label = QLabel(f"<b>{status_name}</b>")
                name_label.setMinimumWidth(150)
                row_layout.addWidget(name_label)

                if status_o['type'] == 'percentage':
                    bar = QProgressBar()
                    bar.setMinimum(0)
                    bar.setMaximum(100)
                    bar.setFixedHeight(18)
                    
                    val = float(status_o['value'])
                    bar.setValue(int(val))
                    
                    if status == 'headset_battery_charge':
                        is_charging = status_obj.get('cable_charging', {}).get('value') == 'on'
                        if is_charging:
                            bar.setStyleSheet("QProgressBar::chunk { background-color: #4caf50; }")
                            bar.setFormat("%p% ⚡")
                        elif val <= 20:
                            bar.setStyleSheet("QProgressBar::chunk { background-color: #f44336; }")
                        else:
                            bar.setStyleSheet("QProgressBar::chunk { background-color: #2196f3; }")
                    elif status in ['chat_mix', 'media_mix']:
                        bar.setStyleSheet("QProgressBar::chunk { background-color: #9c27b0; }")
                        
                    row_layout.addWidget(bar)
                else:
                    val_str = I18n.translate('status_values', status_o['value'])
                    
                    # Add some visual flair for specific status types
                    if status == 'cable_charging':
                        if status_o['value'] == 'on':
                            val_str = "⚡ " + val_str
                        else:
                            val_str = "🔌 " + val_str
                    elif status == 'bluetooth_connection':
                        if status_o['value'] == 'connected':
                            val_str = "🔵 " + val_str
                        else:
                            val_str = "⚪ " + val_str
                    elif status == 'headset_power_status':
                        if status_o['value'] == 'online':
                            val_str = "🟢 " + val_str
                        elif status_o['value'] == 'charging':
                            val_str = "🟡 " + val_str
                        else:
                            val_str = "🔴 " + val_str
                            
                    val_label = QLabel(val_str)
                    row_layout.addWidget(val_label)
                    row_layout.addStretch()

                self.main_layout.addWidget(row_widget)
