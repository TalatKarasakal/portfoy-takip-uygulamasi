from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import QVariantAnimation, Qt
from app.utils.formatters import format_currency, format_percent

class KPICard(QWidget):
    def __init__(self, title: str, formatter_type: str = "currency"):
        super().__init__()
        self.setProperty("class", "CardWidget")
        self.formatter_type = formatter_type
        self.current_value = 0.0
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "CardTitle")
        
        self.value_label = QLabel(self._format(self.current_value))
        self.value_label.setProperty("class", "CardValue")
        self.value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addStretch()

        self.animation = QVariantAnimation(self)
        self.animation.setDuration(400) # 400ms yumuşak sayaç
        self.animation.valueChanged.connect(self._on_animation_value_changed)

    def _format(self, value: float) -> str:
        if self.formatter_type == "currency":
            return format_currency(value)
        elif self.formatter_type == "percent":
            return format_percent(value)
        return str(value)

    def set_value(self, target_value: float, colored: bool = False):
        if self.current_value == target_value:
            return
            
        self.animation.stop()
        self.animation.setStartValue(self.current_value)
        self.animation.setEndValue(target_value)
        self.animation.start()
        
        self.current_value = target_value
        
        if colored:
            if target_value > 0:
                self.value_label.setProperty("class", "CardValue ProfitText")
            elif target_value < 0:
                self.value_label.setProperty("class", "CardValue LossText")
            else:
                self.value_label.setProperty("class", "CardValue")
            
            # Repolish is required to re-evaluate QSS properties
            self.value_label.style().unpolish(self.value_label)
            self.value_label.style().polish(self.value_label)

    def _on_animation_value_changed(self, value: float):
        self.value_label.setText(self._format(float(value)))
