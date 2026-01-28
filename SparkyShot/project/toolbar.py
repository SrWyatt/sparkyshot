from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QPushButton, QSlider, QColorDialog,
                             QDialog, QFrame, QLabel, QSpinBox, QVBoxLayout, QInputDialog)
from PyQt6.QtGui import QIcon, QColor, QPen, QCursor, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal, QSize
import os

class AboutDialog(QDialog):
    def __init__(self, icons_path):
        super().__init__()
        self.icons_path = icons_path
        self.setWindowTitle("About SparkyShot")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.MSWindowsFixedSizeDialogHint)
        self.setFixedSize(400, 220)

        self.setStyleSheet("""
            QDialog { background-color: #171718; border: 1px solid #333; }
            QLabel { color: #E0E0E0; font-family: 'Segoe UI', sans-serif; }
            QPushButton {
                background-color: #333333;
                color: white;
                border: 1px solid #444;
                border-radius: 5px;
                padding: 6px 20px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #444444; border-color: #555; }
            QPushButton:pressed { background-color: #222; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        lbl_img = QLabel()
        logo_path = os.path.join(self.icons_path, "logo_sparkyshot_svg.svg")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            lbl_img.setPixmap(pix.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

        lbl_img.setStyleSheet("background-color: transparent; padding: 10px;")
        lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_layout = QVBoxLayout()
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_title = QLabel("SparkyShot")
        lbl_title.setStyleSheet("font-size: 22px; font-weight: bold; color: white;")

        lbl_ver = QLabel("Version 1.0")
        lbl_ver.setStyleSheet("font-size: 14px; color: #888; margin-bottom: 10px;")

        lbl_credits = QLabel("Created by: SrWyatt\n2026")
        lbl_credits.setStyleSheet("font-size: 14px; color: #ccc;")

        text_layout.addWidget(lbl_title)
        text_layout.addWidget(lbl_ver)
        text_layout.addWidget(lbl_credits)
        text_layout.addStretch()

        btn_ok = QPushButton("OK")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.clicked.connect(self.accept)
        text_layout.addWidget(btn_ok, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addWidget(lbl_img)
        layout.addLayout(text_layout)

class SliderDialog(QDialog):
    def __init__(self, title, current_val, min_val, max_val, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setStyleSheet("""
            QFrame#MainFrame {
                background-color: #1e1e1e;
                border: 1px solid #444;
                border-radius: 8px;
            }
            QLabel { color: #f0f0f0; font-weight: bold; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
            QLabel#Title { color: #aaa; font-size: 11px; margin-bottom: 5px; }

            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0099ff; }

            QSlider::groove:horizontal {
                border: 1px solid #333;
                height: 4px;
                background: #333;
                margin: 2px 0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: white;
                border: 1px solid #ccc;
                width: 14px;
                height: 14px;
                margin: -6px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #f0f0f0;
                border-color: white;
            }
            QSlider::sub-page:horizontal {
                background: #007acc;
                border-radius: 2px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setObjectName("MainFrame")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(15, 15, 15, 15)

        lbl_title = QLabel(title.upper())
        lbl_title.setObjectName("Title")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        frame_layout.addWidget(lbl_title)

        row = QHBoxLayout()
        row.setSpacing(10)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(current_val)
        self.slider.setFixedWidth(140)

        self.label = QLabel(f"{current_val}")
        self.label.setFixedWidth(30)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.slider.valueChanged.connect(self.update_label)

        row.addWidget(self.slider)
        row.addWidget(self.label)
        frame_layout.addLayout(row)

        btn_ok = QPushButton("OK")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.clicked.connect(self.accept)
        frame_layout.addWidget(btn_ok, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addWidget(frame)

    def update_label(self, value):
        self.label.setText(f"{value}")

    def get_value(self):
        return self.slider.value()

class EditorToolbar(QWidget):
    tool_selected = pyqtSignal(str)
    color_changed = pyqtSignal(QColor)
    size_changed = pyqtSignal(int)
    zoom_changed = pyqtSignal(int)
    zoom_in_signal = pyqtSignal()
    zoom_out_signal = pyqtSignal()
    undo_signal = pyqtSignal()
    redo_signal = pyqtSignal()
    save_signal = pyqtSignal()
    copy_signal = pyqtSignal()
    sides_signal = pyqtSignal(int)

    blur_changed = pyqtSignal(int)
    pixel_changed = pyqtSignal(int)
    text_size_changed = pyqtSignal(int)

    def __init__(self, icons_path):
        super().__init__()
        self.icons_path = icons_path
        self.current_size = 5
        self.current_sides = 6

        self.blur_intensity = 15
        self.pixel_intensity = 10
        self.text_size = 24

        self.tool_buttons = {}
        self.active_tool = "cursor"

        self.initUI()

    def initUI(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)
        self.setLayout(layout)

        self.setStyleSheet("""
            QWidget { background-color: #171718; border-bottom: 1px solid #333; }
            QLabel { color: #aaa; font-weight: bold; }
            QSlider::groove:horizontal {
                height: 4px; background: #333; border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #888; width: 12px; margin: -4px 0; border-radius: 6px;
            }
            QSlider::handle:horizontal:hover { background: white; }
            QSlider::sub-page:horizontal { background: #666; border-radius: 2px; }
        """)

        self.btn_logo = QPushButton()
        logo_path = os.path.join(self.icons_path, "logo_sparkyshot_svg.svg")
        if os.path.exists(logo_path):
            self.btn_logo.setIcon(QIcon(logo_path))
            self.btn_logo.setIconSize(QSize(22, 22))

        self.btn_logo.setFixedSize(32, 32)
        self.btn_logo.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                border-radius: 6px;
                border: 1px solid #555;
            }
            QPushButton:hover {
                background-color: white;
            }
        """)
        self.btn_logo.setToolTip("About SparkyShot")
        self.btn_logo.clicked.connect(self.open_about)
        layout.addWidget(self.btn_logo)

        layout.addSpacing(10)
        self.add_separator(layout)
        layout.addSpacing(5)

        self.add_btn(layout, "tool_cursor.svg", "cursor", "Move")
        self.add_separator(layout)
        self.add_btn(layout, "tool_freehand.svg", "pen", "Freehand Marker")
        self.add_btn(layout, "tool_arrow.svg", "arrow", "Arrow")
        self.add_btn(layout, "tool_rect.svg", "rect", "Rectangle")
        self.add_btn(layout, "tool_circle.svg", "circle", "Circle")

        btn_poly = self.add_btn(layout, "tool_polygon.svg", "polygon", "Polygon")
        btn_poly.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        btn_poly.customContextMenuRequested.connect(self.ask_sides)

        btn_text = self.add_btn(layout, "tool_text.svg", "text", "Text (Right-click for size)")
        btn_text.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        btn_text.customContextMenuRequested.connect(self.open_text_size_dialog)

        layout.addSpacing(10)

        btn_pixel = self.add_btn(layout, "tool_pixelate.svg", "pixelate", "Pixelate (Right-click for size)")
        btn_pixel.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        btn_pixel.customContextMenuRequested.connect(self.open_pixel_dialog)

        btn_blur = self.add_btn(layout, "tool_blur.svg", "blur", "Blur (Right-click for intensity)")
        btn_blur.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        btn_blur.customContextMenuRequested.connect(self.open_blur_dialog)

        layout.addStretch()

        self.btn_color = self.add_btn(layout, "settings_color.svg", "color", "Color")
        try: self.btn_color.clicked.disconnect()
        except: pass
        self.btn_color.clicked.connect(self.choose_color)

        self.btn_size = self.add_btn(layout, "settings_size.svg", "size", "Size")
        try: self.btn_size.clicked.disconnect()
        except: pass
        self.btn_size.clicked.connect(self.open_size_dialog)

        layout.addSpacing(15)

        self.add_btn(layout, "action_zoom_out.svg", "zoom_out", "Zoom Out")

        self.slider_zoom = QSlider(Qt.Orientation.Horizontal)
        self.slider_zoom.setRange(10, 200)
        self.slider_zoom.setValue(100)
        self.slider_zoom.setFixedWidth(80)
        self.slider_zoom.valueChanged.connect(lambda v: self.zoom_changed.emit(v))
        layout.addWidget(self.slider_zoom)

        self.add_btn(layout, "action_zoom_in.svg", "zoom_in", "Zoom In")

        layout.addSpacing(15)

        self.add_btn(layout, "action_undo.svg", "undo", "Undo")
        self.add_btn(layout, "action_redo.svg", "redo", "Redo")
        self.add_btn(layout, "action_copy.svg", "copy", "Copy to Clipboard")
        self.add_btn(layout, "action_save.svg", "save", "Save Image")

        self.update_active_tool("cursor")

    def add_btn(self, layout, icon_name, mode, tooltip):
        btn = QPushButton()
        icon_path = os.path.join(self.icons_path, icon_name)

        if os.path.exists(icon_path):
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(20, 20))
            btn.setFixedSize(32, 32)
        else:
            if mode == "zoom_in": btn.setText("+")
            elif mode == "zoom_out": btn.setText("-")
            else: btn.setText(mode[0].upper())

        btn.setToolTip(tooltip)

        if mode == "undo": btn.clicked.connect(self.undo_signal.emit)
        elif mode == "redo": btn.clicked.connect(self.redo_signal.emit)
        elif mode == "copy": btn.clicked.connect(self.copy_signal.emit)
        elif mode == "save": btn.clicked.connect(self.save_signal.emit)
        elif mode == "zoom_in": btn.clicked.connect(self.zoom_in_signal.emit)
        elif mode == "zoom_out": btn.clicked.connect(self.zoom_out_signal.emit)
        elif mode not in ["color", "size"]:
            btn.clicked.connect(lambda: self.on_tool_clicked(mode))

        if mode not in ["undo", "redo", "copy", "save", "zoom_in", "zoom_out", "color", "size"]:
            self.tool_buttons[mode] = btn

        layout.addWidget(btn)
        return btn

    def on_tool_clicked(self, mode):
        self.tool_selected.emit(mode)
        self.update_active_tool(mode)

    def update_active_tool(self, mode):
        self.active_tool = mode

        style_inactive = """
            QPushButton {
                border: none;
                border-radius: 4px;
                padding: 2px;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """

        style_active = """
            QPushButton {
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                padding: 2px;
                background-color: rgba(255, 255, 255, 0.15);
            }
        """

        for key, btn in self.tool_buttons.items():
            if key == mode:
                btn.setStyleSheet(style_active)
            else:
                btn.setStyleSheet(style_inactive)

    def add_separator(self, layout):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("background-color: #444; width: 1px;")
        line.setFixedWidth(1)
        layout.addWidget(line)

    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.color_changed.emit(color)

    def open_size_dialog(self):
        dlg = SliderDialog("Stroke Size", self.current_size, 1, 50, self)
        geo = self.btn_size.mapToGlobal(self.btn_size.rect().bottomLeft())
        dlg.move(geo.x(), geo.y() + 5)
        if dlg.exec():
            val = dlg.get_value()
            self.current_size = val
            self.size_changed.emit(val)

    def open_pixel_dialog(self):
        dlg = SliderDialog("Pixel Size", self.pixel_intensity, 2, 100, self)
        dlg.move(QCursor.pos())
        if dlg.exec():
            val = dlg.get_value()
            self.pixel_intensity = val
            self.pixel_changed.emit(val)

    def open_blur_dialog(self):
        dlg = SliderDialog("Blur Intensity", self.blur_intensity, 1, 100, self)
        dlg.move(QCursor.pos())
        if dlg.exec():
            val = dlg.get_value()
            self.blur_intensity = val
            self.blur_changed.emit(val)

    def open_text_size_dialog(self):
        dlg = SliderDialog("Text Font Size", self.text_size, 8, 120, self)
        dlg.move(QCursor.pos())
        if dlg.exec():
            val = dlg.get_value()
            self.text_size = val
            self.text_size_changed.emit(val)

    def open_about(self):
        dlg = AboutDialog(self.icons_path)
        dlg.exec()

    def ask_sides(self):
        i, ok = QInputDialog.getInt(self, "Polygon", "Sides:", self.current_sides, 3, 20, 1)
        if ok:
            self.current_sides = i
            self.sides_signal.emit(i)

    def set_zoom_value(self, value):
        self.slider_zoom.blockSignals(True)
        self.slider_zoom.setValue(value)
        self.slider_zoom.blockSignals(False)
