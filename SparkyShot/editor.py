from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene,
                             QGraphicsPixmapItem, QMessageBox, QFileDialog,
                             QInputDialog, QApplication, QGraphicsPathItem)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QPainterPath, QPixmap, QFont, QCursor
import math
import numpy as np
import cv2

from toolbar import EditorToolbar
from utils import calculate_ngon_points, convert_qpixmap_to_opencv, apply_pixelate, apply_blur, convert_opencv_to_qpixmap

class EditorView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.parent_editor = parent
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        # Cambio: Habilitamos SmoothPixmapTransform junto con Antialiasing en la vista
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)

    def mousePressEvent(self, event):
        if self.parent_editor.current_tool != "cursor" and event.button() == Qt.MouseButton.LeftButton:
            self.parent_editor.start_drawing(self.mapToScene(event.pos()))
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.parent_editor.is_drawing:
            self.parent_editor.update_drawing(self.mapToScene(event.pos()))
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.parent_editor.is_drawing and event.button() == Qt.MouseButton.LeftButton:
            self.parent_editor.finish_drawing(self.mapToScene(event.pos()))
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.parent_editor.zoom_in()
            else:
                self.parent_editor.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

class EditorWindow(QWidget):
    closed_signal = pyqtSignal()

    def __init__(self, pixmap, icons_path, mode="region"):
        super().__init__()
        self.icons_path = icons_path
        self.pixmap = pixmap
        self.mode = mode

        self.current_tool = "cursor"
        self.current_color = QColor(255, 0, 0)
        self.current_size = 5

        self.blur_intensity = 15
        self.pixel_intensity = 10
        self.text_size = 24

        self.polygon_sides = 6
        self.items_drawn = []
        self.redo_stack = []
        self.is_drawing = False
        self.temp_item = None
        self.start_point = None
        self.current_path = None
        self.bypass_close_confirm = False

        self.initUI()

    def initUI(self):
        self.setWindowTitle("SparkyShot Editor")
        self.setWindowFlags(Qt.WindowType.Window)

        self.setStyleSheet("background-color: #171718;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.toolbar = EditorToolbar(self.icons_path)
        self.connect_toolbar()
        main_layout.addWidget(self.toolbar)

        self.scene = QGraphicsScene()
        self.view = EditorView(self.scene, self)

        self.view.setStyleSheet("border: none; background-color: #1e1e1e;")
        main_layout.addWidget(self.view)

        self.bg_item = QGraphicsPixmapItem(self.pixmap)
        # Cambio: Habilitamos el modo de transformación suave en la imagen de fondo
        self.bg_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.bg_item.setZValue(0)
        self.scene.addItem(self.bg_item)
        self.scene.setSceneRect(QRectF(self.pixmap.rect()))

        w = min(self.pixmap.width() + 50, 1200)
        h = min(self.pixmap.height() + 100, 800)
        self.resize(w, h)

    def connect_toolbar(self):
        self.toolbar.tool_selected.connect(self.set_tool)
        self.toolbar.color_changed.connect(lambda c: setattr(self, 'current_color', c))
        self.toolbar.size_changed.connect(lambda s: setattr(self, 'current_size', s))

        self.toolbar.blur_changed.connect(lambda v: setattr(self, 'blur_intensity', v))
        self.toolbar.pixel_changed.connect(lambda v: setattr(self, 'pixel_intensity', v))
        self.toolbar.text_size_changed.connect(lambda v: setattr(self, 'text_size', v))

        self.toolbar.sides_signal.connect(lambda s: setattr(self, 'polygon_sides', s))
        self.toolbar.undo_signal.connect(self.undo_last)
        self.toolbar.redo_signal.connect(self.redo_last)
        self.toolbar.zoom_changed.connect(self.set_zoom)
        self.toolbar.zoom_in_signal.connect(self.zoom_in)
        self.toolbar.zoom_out_signal.connect(self.zoom_out)
        self.toolbar.copy_signal.connect(self.finish_copy)
        self.toolbar.save_signal.connect(self.finish_save)

    def set_tool(self, tool):
        self.current_tool = tool
        if tool == "cursor":
            self.view.setCursor(Qt.CursorShape.ArrowCursor)
            self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        elif tool == "text":
            self.view.setCursor(Qt.CursorShape.IBeamCursor)
            self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
        else:
            self.view.setCursor(Qt.CursorShape.CrossCursor)
            self.view.setDragMode(QGraphicsView.DragMode.NoDrag)

    def start_drawing(self, pos):
        self.redo_stack.clear()
        self.is_drawing = True
        self.start_point = pos

        if self.current_tool in ["blur", "pixelate"]:
            pen = QPen(Qt.GlobalColor.white, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        else:
            pen = QPen(self.current_color, self.current_size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)

        if self.current_tool == "pen":
            self.current_path = QPainterPath()
            self.current_path.moveTo(pos)
            self.temp_item = self.scene.addPath(self.current_path, pen)

        elif self.current_tool in ["rect", "blur", "pixelate", "circle"]:
            if self.current_tool == "circle":
                self.temp_item = self.scene.addEllipse(QRectF(pos, pos), pen)
            else:
                self.temp_item = self.scene.addRect(QRectF(pos, pos), pen)

        elif self.current_tool in ["arrow", "polygon"]:
            self.temp_item = self.scene.addPath(QPainterPath(), pen)

    def update_drawing(self, pos):
        if not self.temp_item: return

        modifiers = QApplication.keyboardModifiers()
        is_shift = modifiers & Qt.KeyboardModifier.ShiftModifier

        if is_shift and self.current_tool in ["rect", "circle", "blur", "pixelate"]:
            dx = pos.x() - self.start_point.x()
            dy = pos.y() - self.start_point.y()
            size = max(abs(dx), abs(dy))
            dx = size if dx >= 0 else -size
            dy = size if dy >= 0 else -size
            new_pos = QPointF(self.start_point.x() + dx, self.start_point.y() + dy)
            rect = QRectF(self.start_point, new_pos).normalized()
        else:
            rect = QRectF(self.start_point, pos).normalized()

        if self.current_tool == "pen":
            if isinstance(self.temp_item, QGraphicsPathItem) and self.current_path:
                self.current_path.lineTo(pos)
                self.temp_item.setPath(self.current_path)

        elif self.current_tool in ["rect", "blur", "pixelate", "circle"]:
            self.temp_item.setRect(rect)

        elif self.current_tool == "arrow":
            self.update_arrow(pos)

        elif self.current_tool == "polygon":
            self.update_polygon(rect)

    def update_arrow(self, pos):
        if not isinstance(self.temp_item, QGraphicsPathItem): return

        path = QPainterPath()
        path.moveTo(self.start_point)
        path.lineTo(pos)

        dx, dy = pos.x() - self.start_point.x(), pos.y() - self.start_point.y()
        angle = math.atan2(dy, dx)
        head_size = self.current_size * 3

        p1 = QPointF(pos.x() - head_size * math.cos(angle - math.pi/6),
                     pos.y() - head_size * math.sin(angle - math.pi/6))
        p2 = QPointF(pos.x() - head_size * math.cos(angle + math.pi/6),
                     pos.y() - head_size * math.sin(angle + math.pi/6))

        path.lineTo(p1)
        path.moveTo(pos)
        path.lineTo(p2)

        self.temp_item.setPath(path)

    def update_polygon(self, rect):
        if not isinstance(self.temp_item, QGraphicsPathItem): return

        radius = math.sqrt(rect.width()**2 + rect.height()**2) / 2
        points = calculate_ngon_points(rect.center().x(), rect.center().y(), radius, self.polygon_sides)

        path = QPainterPath()
        if points:
            path.moveTo(QPointF(*points[0]))
            for p in points[1:]:
                path.lineTo(QPointF(*p))
            path.closeSubpath()

        self.temp_item.setPath(path)

    def finish_drawing(self, pos):
        self.is_drawing = False
        self.current_path = None

        if self.current_tool == "text":
            text, ok = QInputDialog.getText(self, "Text", "Content:")
            if ok and text:
                item = self.scene.addText(text)
                item.setPos(pos)
                item.setDefaultTextColor(self.current_color)
                item.setFont(QFont("Arial", self.text_size))
                self.items_drawn.append(item)
            return

        if self.current_tool in ["blur", "pixelate"]:
            if self.temp_item:
                rect = self.temp_item.rect().toRect()
                self.scene.removeItem(self.temp_item)
                self.temp_item = None
                self.apply_effect(rect)
            return

        if self.temp_item:
            self.items_drawn.append(self.temp_item)
            self.temp_item = None

    def apply_effect(self, rect):
        if rect.isEmpty(): return
        img_rect = self.bg_item.boundingRect().toRect()
        intersect = rect.intersected(img_rect)
        if intersect.isEmpty(): return

        base_pix = self.bg_item.pixmap().copy(intersect)
        cv_img = convert_qpixmap_to_opencv(base_pix)

        if self.current_tool == "pixelate":
            cv_res = apply_pixelate(cv_img, 0, 0, intersect.width(), intersect.height(), self.pixel_intensity)
        else:
            ksize = (self.blur_intensity * 2) + 1
            cv_res = apply_blur(cv_img, 0, 0, intersect.width(), intersect.height(), ksize)

        patch = QGraphicsPixmapItem(convert_opencv_to_qpixmap(cv_res))
        patch.setPos(QPointF(intersect.topLeft()))
        self.scene.addItem(patch)
        self.items_drawn.append(patch)

    def undo_last(self):
        if self.items_drawn:
            item = self.items_drawn.pop()
            self.scene.removeItem(item)
            self.redo_stack.append(item)

    def redo_last(self):
        if self.redo_stack:
            item = self.redo_stack.pop()
            self.scene.addItem(item)
            self.items_drawn.append(item)

    def zoom_in(self):
        self.view.scale(1.2, 1.2)
        self.update_zoom_slider()

    def zoom_out(self):
        self.view.scale(0.8, 0.8)
        self.update_zoom_slider()

    def set_zoom(self, value):
        factor = value / 100.0
        self.view.resetTransform()
        self.view.scale(factor, factor)

    def update_zoom_slider(self):
        factor = self.view.transform().m11()
        self.toolbar.set_zoom_value(int(factor * 100))

    def set_zoom_slider_val(self, val):
        self.toolbar.slider_zoom.blockSignals(True)
        self.toolbar.slider_zoom.setValue(val)
        self.toolbar.slider_zoom.blockSignals(False)

    def finish_copy(self):
        self.scene.clearSelection()
        img = self.render_final()
        QApplication.clipboard().setPixmap(img)
        self.bypass_close_confirm = True
        self.close()

    def finish_save(self):
        self.scene.clearSelection()
        img = self.render_final()
        path, _ = QFileDialog.getSaveFileName(self, "Save Image", "screenshot.png", "PNG (*.png)")
        if path:
            img.save(path)
            self.bypass_close_confirm = True
            self.close()

    def render_final(self):
        r = self.scene.sceneRect()
        img = QPixmap(r.size().toSize())
        img.fill(Qt.GlobalColor.transparent)
        painter = QPainter(img)
        self.scene.render(painter)
        painter.end()
        return img

    def closeEvent(self, event):
        if not self.bypass_close_confirm:
            reply = QMessageBox()
            reply.setWindowTitle("Exit Editor")
            reply.setText("Are you sure you want to close? Unsaved changes will be lost.")
            reply.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            reply.setDefaultButton(QMessageBox.StandardButton.No)

            reply.setStyleSheet("""
                QMessageBox { background-color: #171718; color: #f0f0f0; }
                QLabel { color: #f0f0f0; }
                QPushButton { background-color: #333; color: white; border: 1px solid #444; padding: 5px 15px; border-radius: 4px; }
                QPushButton:hover { background-color: #444; border-color: #666; }
            """)
            ret = reply.exec()
            if ret == QMessageBox.StandardButton.No:
                event.ignore()
                return
        self.closed_signal.emit()
