from PySide6.QtCore import Qt, QVariantAnimation
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.utils.display import display
from app.utils.formatters import format_percent


class KPICard(QWidget):
    def __init__(self, title: str, formatter_type: str = "currency"):
        super().__init__()
        self.setProperty("class", "CardWidget")
        self.formatter_type = formatter_type
        self.current_value = 0.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "CardTitle")

        self.value_label = QLabel(self._format(self.current_value))
        self.value_label.setProperty("class", "CardValue")
        self.value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # İkincil satır (USD karşılığı, yüzde, ikinci pozisyon vb.)
        self.subtitle_label = QLabel("")
        self.subtitle_label.setProperty("class", "CardSubtitle")
        self.subtitle_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.subtitle_label.setVisible(False)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.subtitle_label)
        layout.addStretch()

        self.animation = QVariantAnimation(self)
        self.animation.setDuration(400)  # 400ms yumuşak sayaç
        self.animation.valueChanged.connect(self._on_animation_value_changed)

    def _format(self, value: float) -> str:
        if self.formatter_type == "currency":
            return display.format(value)
        elif self.formatter_type == "percent":
            return format_percent(value)
        return str(value)

    def _apply_color_class(self, label: QLabel, base: str, value: float, colored: bool):
        if colored:
            if value > 0:
                label.setProperty("class", f"{base} ProfitText")
            elif value < 0:
                label.setProperty("class", f"{base} LossText")
            else:
                label.setProperty("class", base)
        else:
            label.setProperty("class", base)
        # QSS property değişiminin yeniden değerlendirilmesi için repolish gerekir.
        label.style().unpolish(label)
        label.style().polish(label)

    def set_value(self, target_value: float, colored: bool = False):
        if self.current_value != target_value:
            self.animation.stop()
            self.animation.setStartValue(self.current_value)
            self.animation.setEndValue(target_value)
            self.animation.start()
            self.current_value = target_value

        self._apply_color_class(self.value_label, "CardValue", target_value, colored)

    def set_primary_text(self, text: str, value_for_color: float = 0.0, colored: bool = False):
        """Sayısal olmayan ana içerik (örn. 'THYAO +12,3%') için animasyonsuz metin."""
        self.animation.stop()
        self.value_label.setText(text)
        self._apply_color_class(self.value_label, "CardValue", value_for_color, colored)

    def set_subtitle(self, text: str, value_for_color: float = 0.0, colored: bool = False):
        self.subtitle_label.setText(text)
        self.subtitle_label.setVisible(bool(text))
        self._apply_color_class(self.subtitle_label, "CardSubtitle", value_for_color, colored)

    def _on_animation_value_changed(self, value: float):
        self.value_label.setText(self._format(float(value)))
