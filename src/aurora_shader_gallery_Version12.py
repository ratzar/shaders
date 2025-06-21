import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QComboBox, QCheckBox, QLineEdit, QTextEdit, QScrollArea,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QColor, QFont

# --- RangeSlider custom widget ---
class QRangeSlider(QWidget):
    valueChanged = pyqtSignal(int, int)

    def __init__(self, min_value=0, max_value=100, start_min=None, start_max=None, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(30)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.min = min_value
        self.max = max_value
        self.left_value = start_min if start_min is not None else min_value
        self.right_value = start_max if start_max is not None else max_value
        self.moving = None  # 'left', 'right', or None
        self.margin = 14
        self.handle_radius = 8
        self.bar_height = 4
        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        w, h = self.width(), self.height()
        # Draw bar
        bar_y = h // 2 - self.bar_height // 2
        bar_rect = QRect(self.margin, bar_y, w - 2*self.margin, self.bar_height)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(55, 58, 75))  # dark bar
        painter.drawRect(bar_rect)
        # Draw selected range
        left = self.value_to_pos(self.left_value)
        right = self.value_to_pos(self.right_value)
        sel_rect = QRect(left, bar_y, right - left, self.bar_height)
        painter.setBrush(QColor(0, 200, 200))
        painter.drawRect(sel_rect)
        # Draw handles
        painter.setBrush(QColor(50, 230, 255) if not self.moving == "left" else QColor(255, 200, 0))
        painter.drawEllipse(QPoint(left, h//2), self.handle_radius, self.handle_radius)
        painter.setBrush(QColor(50, 230, 255) if not self.moving == "right" else QColor(255, 200, 0))
        painter.drawEllipse(QPoint(right, h//2), self.handle_radius, self.handle_radius)
        # Draw values
        painter.setPen(QColor("white"))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(left-18, h//2-10, f"{self.left_value}")
        painter.drawText(right+6, h//2-10, f"{self.right_value}")

    def value_to_pos(self, value):
        usable_w = self.width() - 2*self.margin
        pos = self.margin + int((value - self.min) / (self.max - self.min) * usable_w)
        return pos

    def pos_to_value(self, pos):
        usable_w = self.width() - 2*self.margin
        val = self.min + (pos - self.margin) / max(1, usable_w) * (self.max - self.min)
        return int(round(max(self.min, min(self.max, val))))

    def mousePressEvent(self, event):
        x = event.position().x()
        left = self.value_to_pos(self.left_value)
        right = self.value_to_pos(self.right_value)
        if abs(x - left) < self.handle_radius + 2:
            self.moving = "left"
        elif abs(x - right) < self.handle_radius + 2:
            self.moving = "right"
        else:
            self.moving = None

    def mouseMoveEvent(self, event):
        if not self.moving:
            return
        x = event.position().x()
        val = self.pos_to_value(x)
        if self.moving == "left":
            val = min(val, self.right_value)
            val = max(self.min, val)
            if val != self.left_value:
                self.left_value = val
                self.valueChanged.emit(self.left_value, self.right_value)
                self.update()
        elif self.moving == "right":
            val = max(val, self.left_value)
            val = min(self.max, val)
            if val != self.right_value:
                self.right_value = val
                self.valueChanged.emit(self.left_value, self.right_value)
                self.update()

    def mouseReleaseEvent(self, event):
        self.moving = None

    def setValues(self, minval, maxval):
        minval = max(self.min, min(self.max, minval))
        maxval = max(self.min, min(self.max, maxval))
        if minval > maxval:
            minval, maxval = maxval, minval
        self.left_value = minval
        self.right_value = maxval
        self.update()
        self.valueChanged.emit(self.left_value, self.right_value)

    def getValues(self):
        return (self.left_value, self.right_value)

# --- Effect Control Widget ---
class EffectControlWidget(QWidget):
    def __init__(self, name, min_range=0, max_range=100, step=1, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setSpacing(2)
        label = QLabel(f"<b>{name}</b>")
        label.setStyleSheet("color: #b1faff; font-size: 12px;")
        layout.addWidget(label)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(min_range, max_range)
        self.slider.setValue((max_range + min_range) // 2)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 6px; background: #444;}
            QSlider::handle:horizontal { background: #00cccc; border-radius: 8px; width: 16px; }
        """)
        layout.addWidget(self.slider)

        self.range_slider = QRangeSlider(min_range, max_range, min_range, max_range)
        layout.addWidget(self.range_slider)

        self.setLayout(layout)
        self.setStyleSheet("background:transparent;")

# --- Main Window ---
class ShaderGalleryMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aurora Shader Gallery")
        self.setMinimumSize(1150, 650)
        self.setStyleSheet("background-color: #1a1a2d; color: #f8f8ff;")

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(12)

        # Left column
        left_col = QVBoxLayout()
        left_col.setSpacing(12)
        btn_folder = QPushButton("Scegli cartella shader")
        btn_folder.setStyleSheet("background:#50d9ff;color:#222;font-weight:bold;font-size:18px;padding:12px;border-radius:6px;")
        btn_bonzomatic = QPushButton("Apri Bonzomatic")
        btn_bonzomatic.setStyleSheet("background:#bd8cff;color:#222;font-weight:bold;font-size:18px;padding:12px;border-radius:6px;")
        btn_shadertoy = QPushButton("Apri ShaderToy")
        btn_shadertoy.setStyleSheet("background:#40eeb9;color:#222;font-weight:bold;font-size:18px;padding:12px;border-radius:6px;")
        left_col.addWidget(btn_folder)
        left_col.addWidget(btn_bonzomatic)
        left_col.addWidget(btn_shadertoy)

        url_row = QHBoxLayout()
        url_input = QLineEdit()
        url_input.setPlaceholderText("Incolla qui l'URL ShaderToy...")
        url_input.setStyleSheet("background:#232332;color:white;padding:7px;")
        btn_download = QPushButton("Download")
        btn_download.setStyleSheet("background:#ffbf47;color:#222;font-weight:bold;padding:6px 18px;border-radius:4px;")
        url_row.addWidget(url_input)
        url_row.addWidget(btn_download)
        left_col.addLayout(url_row)

        gal_label = QLabel("<b>Galleria Shader</b>")
        gal_label.setStyleSheet("color:#b1faff;font-size:16px;")
        left_col.addWidget(gal_label)

        gallery_box = QTextEdit()
        gallery_box.setReadOnly(True)
        gallery_box.setStyleSheet("background:#18182b;color:#aaa;border-radius:8px;")
        gallery_box.setMinimumSize(500, 320)
        left_col.addWidget(gallery_box)

        btn_preview = QPushButton("Preview Shader")
        btn_preview.setStyleSheet("color:white;padding:8px;border:2px solid white;border-radius:8px;background:transparent;")
        left_col.addWidget(btn_preview)
        left_col.addStretch(1)
        main_layout.addLayout(left_col, 32)

        # Right column (effects and controls)
        right_col = QVBoxLayout()
        # Header row
        header_row = QHBoxLayout()
        title = QLabel("<span style='color:#b1faff;font-size:28px;font-weight:bold;'>Console Effetti Live</span>")
        header_row.addWidget(title)
        header_row.addStretch(1)
        chk_popup = QCheckBox("Pop up")
        chk_popup.setStyleSheet("color:#b1faff;")
        header_row.addWidget(chk_popup)
        right_col.addLayout(header_row)

        # Video/audio controls
        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)
        lbl_source = QLabel("Sorgente Video:")
        lbl_source.setStyleSheet("color:#b1faff;")
        controls_row.addWidget(lbl_source)
        cb_source = QComboBox()
        cb_source.addItems(["Shader", "Webcam", "Altro"])
        cb_source.setStyleSheet("background:#232332;color:#b1faff;")
        controls_row.addWidget(cb_source)
        controls_row.addSpacing(14)
        lbl_tr = QLabel("Trasparenza:")
        lbl_tr.setStyleSheet("color:#b1faff;")
        controls_row.addWidget(lbl_tr)
        slider_tr = QSlider(Qt.Orientation.Horizontal)
        slider_tr.setRange(0, 100)
        slider_tr.setValue(60)
        slider_tr.setStyleSheet("QSlider::groove:horizontal{height:6px;background:#444;}QSlider::handle:horizontal{background:#00cccc;border-radius:8px;width:16px;}")
        controls_row.addWidget(slider_tr)
        controls_row.addSpacing(14)
        lbl_ck = QLabel("Chroma Key:")
        lbl_ck.setStyleSheet("color:#b1faff;")
        controls_row.addWidget(lbl_ck)
        slider_ck = QSlider(Qt.Orientation.Horizontal)
        slider_ck.setRange(0, 100)
        slider_ck.setValue(20)
        slider_ck.setStyleSheet("QSlider::groove:horizontal{height:6px;background:#444;}QSlider::handle:horizontal{background:#ffbf47;border-radius:8px;width:16px;}")
        controls_row.addWidget(slider_ck)
        controls_row.addSpacing(2)
        chk_luma = QCheckBox("Attiva Chroma Key (Luma)")
        chk_luma.setStyleSheet("color:#b1faff;")
        controls_row.addWidget(chk_luma)
        right_col.addLayout(controls_row)

        # Audio controls
        audio_row = QHBoxLayout()
        lbl_audio = QLabel("Ingresso Audio:")
        lbl_audio.setStyleSheet("color:#b1faff;")
        audio_row.addWidget(lbl_audio)
        cb_audio = QComboBox()
        cb_audio.addItems(["Microfono", "Line-In", "Off"])
        cb_audio.setStyleSheet("background:#232332;color:#b1faff;")
        audio_row.addWidget(cb_audio)
        chk_ardetect = QCheckBox("Audio React")
        chk_ardetect.setStyleSheet("color:#b1faff;")
        audio_row.addWidget(chk_ardetect)
        btn_tap = QPushButton("TAP")
        btn_tap.setStyleSheet("background:#ffbf47;color:#222;font-weight:bold;padding:7px 18px;border-radius:5px;")
        audio_row.addWidget(btn_tap)
        lbl_bpm = QLabel("BPM:")
        lbl_bpm.setStyleSheet("color:#b1faff;")
        audio_row.addWidget(lbl_bpm)
        bpm_edit = QLineEdit("120")
        bpm_edit.setMaximumWidth(50)
        bpm_edit.setStyleSheet("background:#232332;color:#b1faff;text-align:center;")
        audio_row.addWidget(bpm_edit)
        chk_autobpm = QCheckBox("Auto BPM")
        chk_autobpm.setStyleSheet("color:#b1faff;")
        audio_row.addWidget(chk_autobpm)
        chk_beatsync = QCheckBox("Beat Sync")
        chk_beatsync.setStyleSheet("color:#b1faff;")
        audio_row.addWidget(chk_beatsync)
        audio_row.addStretch(1)
        right_col.addLayout(audio_row)

        # Effects scroll area
        effects_scroll = QScrollArea()
        effects_scroll.setWidgetResizable(True)
        effects_scroll.setStyleSheet("background:transparent;")
        effects_widget = QWidget()
        effects_layout = QVBoxLayout(effects_widget)
        effects_layout.setContentsMargins(8, 8, 8, 8)
        effects_layout.setSpacing(18)
        lbl_eff = QLabel("<b>Effetti Video</b>")
        lbl_eff.setStyleSheet("color:#b1faff;font-size:16px;")
        effects_layout.addWidget(lbl_eff)

        fx_params = [
            ("Zoom", 0, 100, 1),
            ("Pan X", -100, 100, 1),
            ("Pan Y", -100, 100, 1),
            ("Rotazione", -180, 180, 1),
            ("Distorsione", 0, 100, 1)
        ]
        for name, mn, mx, step in fx_params:
            eff = EffectControlWidget(name, mn, mx, step)
            effects_layout.addWidget(eff)

        effects_layout.addStretch(1)
        effects_widget.setLayout(effects_layout)
        effects_scroll.setWidget(effects_widget)
        right_col.addWidget(effects_scroll)

        main_layout.addLayout(right_col, 55)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ShaderGalleryMainWindow()
    win.show()
    sys.exit(app.exec())