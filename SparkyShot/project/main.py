import sys
import os
from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout, QPushButton, QLabel, QFrame
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QIcon, QPixmap

from snipper import Snipper
from editor import EditorWindow
from toolbar import AboutDialog
from utils import resource_path, load_svg_icon

class FloatingToolbar(QWidget):
    def __init__(self):
        super().__init__()
        self.snipper = None
        self.editor = None
        self.drag_pos = None
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        container = QFrame(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        container.setObjectName("MainWidget")
        container.setStyleSheet("""
            QFrame#MainWidget {
                background-color: #171718;
                border-radius: 14px;
                border: 1px solid #333;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)

        self.icons_path = resource_path('icons')

        self.btn_logo = QPushButton()
        logo_path = os.path.join(self.icons_path, "logo_sparkyshot_svg.svg")
        self.btn_logo.setIcon(load_svg_icon(logo_path))
        self.btn_logo.setIconSize(QSize(26, 26))

        self.btn_logo.setFixedSize(36, 36)
        self.btn_logo.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                border-radius: 8px;
                border: 1px solid #555;
            }
            QPushButton:hover {
                background-color: white;
            }
        """)
        self.btn_logo.setToolTip("About SparkyShot")
        self.btn_logo.clicked.connect(self.open_about)
        layout.addWidget(self.btn_logo)

        layout.addSpacing(5)

        self.create_btn(layout, "cap_region.svg", "Region Capture", lambda: self.prepare_capture("region"))
        self.create_btn(layout, "cap_fullscreen.svg", "Fullscreen", lambda: self.prepare_capture("fullscreen"))
        self.create_btn(layout, "cap_qr.svg", "Scan QR", lambda: self.prepare_capture("qr"))

        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("background-color: #444; margin: 2px;")
        line.setFixedWidth(1)
        layout.addWidget(line)

        self.create_btn(layout, "action_close.svg", "Exit", self.close)

        self.btn_move = QPushButton()
        move_path = os.path.join(self.icons_path, "tool_move.svg")
        self.btn_move.setIcon(load_svg_icon(move_path))
        self.btn_move.setIconSize(QSize(20, 20))
        self.btn_move.setCursor(Qt.CursorShape.SizeAllCursor)
        self.btn_move.installEventFilter(self)
        self.btn_move.setStyleSheet("QPushButton:hover { background-color: transparent; }")
        layout.addWidget(self.btn_move)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        self.center_top()

    def create_btn(self, layout, icon_name, tooltip, action):
        btn = QPushButton()
        path = os.path.join(self.icons_path, icon_name)
        btn.setIcon(load_svg_icon(path))
        btn.setIconSize(QSize(28, 28))
        btn.setFixedSize(38, 38)
        btn.setToolTip(tooltip)
        btn.clicked.connect(action)
        layout.addWidget(btn)

    def center_top(self):
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - 380) // 2, 80)

    def open_about(self):
        dlg = AboutDialog(self.icons_path)
        dlg.exec()

    def prepare_capture(self, mode):
        self.hide()
        QApplication.processEvents()
        QTimer.singleShot(250, lambda: self.start_snip(mode))

    def start_snip(self, mode):
        self.snipper = Snipper(self.icons_path, mode)
        self.snipper.captured_signal.connect(self.open_editor)
        self.snipper.closed_signal.connect(self.on_snipper_closed)
        if mode != "fullscreen":
            self.snipper.show()

    def on_snipper_closed(self):
        if not self.editor or not self.editor.isVisible():
            self.show()

    def open_editor(self, pixmap, mode):
        self.editor = EditorWindow(pixmap, self.icons_path, mode)
        self.editor.closed_signal.connect(self.show)
        self.editor.show()

    def eventFilter(self, source, event):
        if source == self.btn_move:
            if event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True
            elif event.type() == event.Type.MouseMove and event.buttons() == Qt.MouseButton.LeftButton and self.drag_pos:
                self.move(event.globalPosition().toPoint() - self.drag_pos)
                return True
        return super().eventFilter(source, event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName("SparkShot")

    icon_path_svg = resource_path(os.path.join("icons", "logo_sparkyshot_svg.svg"))
    if os.path.exists(icon_path_svg):
        app.setWindowIcon(QIcon(icon_path_svg))
    else:
        icon_path_png = resource_path(os.path.join("icons", "logo_sparkyshot.png"))
        if os.path.exists(icon_path_png):
             app.setWindowIcon(QIcon(icon_path_png))

    if os.name == 'nt':
        try:
            from ctypes import windll
            windll.shell32.SetCurrentProcessExplicitAppUserModelID('sparkyshot.app.1.0')
        except:
            pass

    window = FloatingToolbar()
    window.show()
    sys.exit(app.exec())
