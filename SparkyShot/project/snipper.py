from PyQt6.QtWidgets import (QWidget, QApplication, QGraphicsView, QGraphicsScene,
                             QMessageBox, QDialog, QVBoxLayout, QLabel, QHBoxLayout,
                             QPushButton, QGraphicsPathItem)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QTimer, QUrl, QSize, QPointF
from PyQt6.QtGui import QPen, QColor, QBrush, QPixmap, QDesktopServices, QIcon, QPainterPath, QPainter
import mss
import numpy as np
import cv2
import os
from utils import convert_opencv_to_qpixmap, convert_qpixmap_to_opencv, detect_qr_content

class QRDialog(QDialog):
    def __init__(self, content, icons_path):
        super().__init__()
        self.content = content
        self.icons_path = icons_path
        self.setWindowTitle("QR Detected")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("""
            QDialog { background-color: #171718; border: 1px solid #444; border-radius: 8px; }
            QLabel { color: white; font-size: 14px; padding: 10px; }
            QPushButton {
                background-color: #333; color: white; border: none; padding: 8px 15px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #555; }
            QPushButton#BtnOpen { background-color: #007acc; }
            QPushButton#BtnClose { background-color: #cc0000; }
            QPushButton#BtnCopy {
                background-color: transparent;
                border: none;
            }
            QPushButton#BtnCopy:hover { background-color: #444; border-radius: 4px; }
        """)

        layout = QVBoxLayout()
        lbl_info = QLabel("Content:")
        lbl_info.setStyleSheet("font-weight: bold; color: #aaa;")
        layout.addWidget(lbl_info)

        lbl_content = QLabel(self.content)
        lbl_content.setWordWrap(True)
        lbl_content.setStyleSheet("background-color: #222; border-radius: 4px; font-family: monospace; padding: 5px;")
        layout.addWidget(lbl_content)

        btn_layout = QHBoxLayout()

        self.btn_copy = QPushButton()
        self.btn_copy.setObjectName("BtnCopy")
        self.btn_copy.setFixedSize(40, 40)
        copy_icon = os.path.join(self.icons_path, "action_copy.svg")
        if os.path.exists(copy_icon):
            self.btn_copy.setIcon(QIcon(copy_icon))
            self.btn_copy.setIconSize(QSize(28, 28))
        else:
            self.btn_copy.setText("C")

        self.btn_copy.setToolTip("Copy to Clipboard")
        self.btn_copy.clicked.connect(self.on_copy)

        self.btn_open = QPushButton("Open")
        self.btn_open.setObjectName("BtnOpen")
        self.btn_open.clicked.connect(self.on_open)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_close = QPushButton("Close")
        self.btn_close.setObjectName("BtnClose")
        self.btn_close.clicked.connect(self.on_close_app)

        btn_layout.addWidget(self.btn_copy)
        btn_layout.addWidget(self.btn_open)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def on_copy(self):
        QApplication.clipboard().setText(self.content)
        self.btn_copy.setStyleSheet("background-color: #225522; border-radius: 4px;")
        QTimer.singleShot(500, lambda: self.btn_copy.setStyleSheet("background-color: transparent; border: none;"))

    def on_open(self):
        url = QUrl(self.content)
        success = QDesktopServices.openUrl(url)
        if not success:
            QMessageBox.critical(self, "Error", "The system could not open this link or application.")
        else:
            self.accept()

    def on_close_app(self):
        self.done(999)

class SnipperView(QGraphicsView):
    """
    Custom GraphicsView to handle selection logic directly.
    """
    def __init__(self, scene, parent_snipper):
        super().__init__(scene)
        self.parent_snipper = parent_snipper
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_snipper.start_selection(self.mapToScene(event.pos()))
        elif event.button() == Qt.MouseButton.RightButton:
            self.parent_snipper.close()

    def mouseMoveEvent(self, event):
        self.parent_snipper.update_selection(self.mapToScene(event.pos()))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_snipper.finish_selection(self.mapToScene(event.pos()))


class Snipper(QWidget):
    captured_signal = pyqtSignal(QPixmap, str)
    closed_signal = pyqtSignal()

    def __init__(self, icons_path, mode="region"):
        super().__init__()
        self.icons_path = icons_path
        self.mode = mode

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowState.WindowFullScreen)

        self.original_pixmap = self.take_screenshot()

        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(QRectF(self.original_pixmap.rect()))

        self.view = SnipperView(self.scene, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

        self.bg_item = self.scene.addPixmap(self.original_pixmap)
        self.bg_item.setZValue(0)

        self.dim_path_item = QGraphicsPathItem()
        self.dim_path_item.setBrush(QBrush(QColor(0, 0, 0, 100)))
        self.dim_path_item.setPen(QPen(Qt.PenStyle.NoPen))
        self.dim_path_item.setZValue(10)
        self.scene.addItem(self.dim_path_item)

        self.update_dimmer(QRectF())

        self.border_pen = QPen(QColor(255, 0, 0), 2, Qt.PenStyle.SolidLine)
        self.selection_rect_item = self.scene.addRect(QRectF(), self.border_pen, QBrush(Qt.BrushStyle.NoBrush))
        self.selection_rect_item.setZValue(20)
        self.selection_rect_item.hide()

        self.start_point = None
        self.is_selecting = False

        if self.mode == "fullscreen":
            QTimer.singleShot(50, lambda: self.finalize_capture(self.original_pixmap))

    def take_screenshot(self):
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            sct_img = sct.grab(monitor)
            img = np.array(sct_img)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            return convert_opencv_to_qpixmap(img)

    def start_selection(self, pos):
        self.start_point = pos
        self.is_selecting = True
        self.selection_rect_item.setRect(QRectF(pos, pos))
        self.selection_rect_item.show()

    def update_selection(self, pos):
        if not self.is_selecting: return

        rect = QRectF(self.start_point, pos).normalized()
        self.selection_rect_item.setRect(rect)
        self.update_dimmer(rect)

    def update_dimmer(self, selection_rect):
        """
        Creates a path that covers the whole screen MINUS the selection_rect.
        """
        path = QPainterPath()
        path.setFillRule(Qt.FillRule.OddEvenFill)

        path.addRect(QRectF(self.original_pixmap.rect()))

        if not selection_rect.isEmpty():
            path.addRect(selection_rect)

        self.dim_path_item.setPath(path)

    def finish_selection(self, pos):
        if not self.is_selecting: return
        self.is_selecting = False
        self.selection_rect_item.hide()

        rect = QRectF(self.start_point, pos).normalized()

        if rect.width() < 5 or rect.height() < 5:
            self.update_dimmer(QRectF())
            return

        if self.mode == "qr":
            self.handle_qr_selection(rect)
        else:
            self.process_rect_capture(rect)

    def handle_qr_selection(self, rect_f):
        rect = rect_f.toRect()
        img_rect = self.original_pixmap.rect()
        safe_rect = rect.intersected(img_rect)

        if safe_rect.width() > 0 and safe_rect.height() > 0:
            cropped = self.original_pixmap.copy(safe_rect)

            cv_raw = convert_qpixmap_to_opencv(cropped)
            content = detect_qr_content(cv_raw)

            if content:
                dialog = QRDialog(content, self.icons_path)
                res = dialog.exec()
                if res == 999:
                    QApplication.quit()
                else:
                    self.close()
            else:
                self.show_message("QR Error", "QR code not available or not detected.")
                self.close()
        else:
            self.close()

    def process_rect_capture(self, rect_f):
        rect = rect_f.toRect()
        if rect.width() > 0 and rect.height() > 0:
            cropped = self.original_pixmap.copy(rect)
            self.finalize_capture(cropped)
        else:
            self.close()

    def finalize_capture(self, pixmap):
        self.captured_signal.emit(pixmap, self.mode)
        self.close()

    def show_message(self, title, text):
        msg = QMessageBox()
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStyleSheet("QMessageBox { background-color: #171718; color: white; } QLabel { color: white; } QPushButton { background-color: #333; color: white; }")
        msg.exec()

    def closeEvent(self, event):
        self.closed_signal.emit()
        super().closeEvent(event)
