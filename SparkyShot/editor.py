import os
import cv2
import numpy as np
import datetime
from PyQt6.QtWidgets import (QMainWindow, QGraphicsView, QGraphicsScene, QWidget,
                             QVBoxLayout, QFileDialog, QApplication, QGraphicsPixmapItem,
                             QInputDialog, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QFont, QAction, QPainterPath, QBrush, QPolygonF

from toolbar import EditorToolbar
from utils import apply_blur, apply_pixelate, calculate_ngon_points, convert_opencv_to_qpixmap, convert_qpixmap_to_opencv

class EditorWindow(QMainWindow):
    closed_signal = pyqtSignal()

    def __init__(self, pixmap, icons_path, capture_mode="region"):
        super().__init__()
        self.icons_path = icons_path
        self.capture_mode = capture_mode
        self.setWindowTitle("SparkyShot Editor")
        self.setGeometry(100, 100, 900, 700)

        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.toolbar = EditorToolbar(self.icons_path)
        layout.addWidget(self.toolbar)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setBackgroundBrush(QColor("#222"))
        layout.addWidget(self.view)

        self.base_pixmap = pixmap
        self.current_pixmap = pixmap.copy()

        self.image_item = QGraphicsPixmapItem(self.current_pixmap)
        self.image_item.setZValue(0)
        self.scene.addItem(self.image_item)

        self.undo_stack = []
        self.redo_stack = []
        self.undo_stack.append(self.current_pixmap.copy())

        self.current_tool = "cursor"
        self.draw_color = QColor(255, 0, 0)
        self.draw_size = 5
        self.blur_val = 15
        self.pixel_val = 10
        self.text_font_size = 24
        self.poly_sides = 6

        self.start_point = None
        self.temp_item = None
        self.is_drawing = False

        self.toolbar.tool_selected.connect(self.set_tool)
        self.toolbar.color_changed.connect(self.set_color)
        self.toolbar.size_changed.connect(self.set_size)
        self.toolbar.blur_changed.connect(self.set_blur)
        self.toolbar.pixel_changed.connect(self.set_pixel)
        self.toolbar.text_size_changed.connect(self.set_text_size)
        self.toolbar.sides_signal.connect(self.set_poly_sides)

        self.toolbar.undo_signal.connect(self.undo_action)
        self.toolbar.redo_signal.connect(self.redo_action)
        self.toolbar.save_signal.connect(self.save_image)
        self.toolbar.copy_signal.connect(self.copy_image)

        self.toolbar.zoom_changed.connect(self.set_zoom)
        self.toolbar.zoom_in_signal.connect(self.zoom_in)
        self.toolbar.zoom_out_signal.connect(self.zoom_out)

        self.view.viewport().installEventFilter(self)

    def set_tool(self, tool_name):
        self.current_tool = tool_name
        if tool_name == "cursor":
            self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.view.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.view.setCursor(Qt.CursorShape.CrossCursor)

    def set_color(self, color):
        self.draw_color = color

    def set_size(self, size):
        self.draw_size = size

    def set_blur(self, val):
        self.blur_val = val

    def set_pixel(self, val):
        self.pixel_val = val

    def set_text_size(self, val):
        self.text_font_size = val

    def set_poly_sides(self, val):
        self.poly_sides = val

    def set_zoom(self, value):
        scale = value / 100.0
        transform = self.view.transform()
        transform.reset()
        transform.scale(scale, scale)
        self.view.setTransform(transform)

    def zoom_in(self):
        val = self.toolbar.slider_zoom.value()
        new_val = min(val + 10, 200)
        self.toolbar.set_zoom_value(new_val)
        self.set_zoom(new_val)

    def zoom_out(self):
        val = self.toolbar.slider_zoom.value()
        new_val = max(val - 10, 10)
        self.toolbar.set_zoom_value(new_val)
        self.set_zoom(new_val)

    def push_undo(self):
        if len(self.undo_stack) > 20:
            self.undo_stack.pop(0)
        self.undo_stack.append(self.current_pixmap.copy())
        self.redo_stack.clear()

    def undo_action(self):
        if len(self.undo_stack) > 1:
            current = self.undo_stack.pop()
            self.redo_stack.append(current)
            prev = self.undo_stack[-1]
            self.current_pixmap = prev.copy()
            self.image_item.setPixmap(self.current_pixmap)

    def redo_action(self):
        if self.redo_stack:
            nxt = self.redo_stack.pop()
            self.undo_stack.append(nxt)
            self.current_pixmap = nxt.copy()
            self.image_item.setPixmap(self.current_pixmap)

    def save_image(self):
        now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_name = f"sparkyshot_{now_str}.png"
        path, _ = QFileDialog.getSaveFileName(self, "Save Image", default_name, "PNG Files (*.png);;JPG Files (*.jpg);;All Files (*)")
        if path:
            self.current_pixmap.save(path)

    def copy_image(self):
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(self.current_pixmap)
        self.toolbar.show_copy_feedback()

    def eventFilter(self, source, event):
        if source == self.view.viewport():
            if event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                if self.current_tool != "cursor":
                    self.start_drawing(event)
                    return True
            elif event.type() == event.Type.MouseMove:
                if self.is_drawing:
                    self.update_drawing(event)
                    return True
            elif event.type() == event.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                if self.is_drawing:
                    self.finish_drawing(event)
                    return True
        return super().eventFilter(source, event)

    def get_draw_rect(self, p1, p2, modifiers):
        x = min(p1.x(), p2.x())
        y = min(p1.y(), p2.y())
        w = abs(p2.x() - p1.x())
        h = abs(p2.y() - p1.y())

        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            side = max(w, h)
            target_x = p1.x() + side if p2.x() >= p1.x() else p1.x() - side
            target_y = p1.y() + side if p2.y() >= p1.y() else p1.y() - side
            return QRectF(p1, QPointF(target_x, target_y)).normalized()

        return QRectF(p1, p2).normalized()

    def get_arrow_point(self, p1, p2, modifiers):
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            dist = (dx**2 + dy**2)**0.5
            if dist > 0:
                angle = np.arctan2(dy, dx)
                step = np.pi / 4
                snapped_angle = round(angle / step) * step
                return QPointF(p1.x() + dist * np.cos(snapped_angle),
                               p1.y() + dist * np.sin(snapped_angle))
        return p2

    def start_drawing(self, event):
        self.is_drawing = True
        sp = self.view.mapToScene(event.pos())
        self.start_point = sp

        if self.current_tool == "text":
            self.handle_text_input(sp)
            self.is_drawing = False
        elif self.current_tool == "pen":
            self.push_undo()

    def update_drawing(self, event):
        if not self.start_point: return

        current_point = self.view.mapToScene(event.pos())

        if self.current_tool == "pen":
            self.paint_on_pixmap(self.current_tool, self.start_point, current_point, final=False)
            self.image_item.setPixmap(self.current_pixmap)
            self.start_point = current_point
        elif self.current_tool in ["rect", "circle", "polygon", "blur", "pixelate"]:
            rect = self.get_draw_rect(self.start_point, current_point, event.modifiers())
            self.refresh_temp_item_rect(rect)
        elif self.current_tool == "arrow":
            endpoint = self.get_arrow_point(self.start_point, current_point, event.modifiers())
            self.refresh_temp_item_arrow(endpoint)

    def finish_drawing(self, event):
        self.is_drawing = False
        end_point = self.view.mapToScene(event.pos())

        if self.temp_item:
            self.scene.removeItem(self.temp_item)
            self.temp_item = None

        if self.current_tool != "pen":
             if self.current_tool == "arrow":
                 final_p2 = self.get_arrow_point(self.start_point, end_point, event.modifiers())
                 self.push_undo()
                 self.paint_arrow(self.start_point, final_p2)
             else:
                 rect = self.get_draw_rect(self.start_point, end_point, event.modifiers())
                 if rect.width() < 2 or rect.height() < 2: return

                 self.push_undo()
                 self.paint_shape(self.current_tool, rect)

             self.image_item.setPixmap(self.current_pixmap)

    def paint_shape(self, tool, rect):
        painter = QPainter(self.current_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self.draw_color, self.draw_size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        if tool == "rect":
            painter.drawRect(rect)
        elif tool == "circle":
            painter.drawEllipse(rect)
        elif tool == "polygon":
            cx, cy = rect.center().x(), rect.center().y()
            rx, ry = rect.width()/2, rect.height()/2
            radius = min(rx, ry)
            points = calculate_ngon_points(cx, cy, radius, self.poly_sides)
            if points:
                qpoints = [QPointF(x, y) for x, y in points]
                painter.drawPolygon(*qpoints)

        painter.end()

        if (tool == "blur" or tool == "pixelate") and not rect.isEmpty():
             cv_img = convert_qpixmap_to_opencv(self.current_pixmap)
             x, y, w, h = int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height())

             if tool == "blur":
                 processed = apply_blur(cv_img, x, y, w, h, self.blur_val)
             else:
                 processed = apply_pixelate(cv_img, x, y, w, h, self.pixel_val)

             self.current_pixmap = convert_opencv_to_qpixmap(processed)

    def paint_arrow(self, p1, p2):
        painter = QPainter(self.current_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self.draw_color, self.draw_size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        line = QPointF(p2.x() - p1.x(), p2.y() - p1.y())
        length = (line.x()**2 + line.y()**2)**0.5

        if length > 0:
            angle = np.arctan2(line.y(), line.x())
            arrow_size = self.draw_size * 3

            p_arrow1 = QPointF(p2.x() - arrow_size * np.cos(angle - np.pi/6),
                               p2.y() - arrow_size * np.sin(angle - np.pi/6))
            p_arrow2 = QPointF(p2.x() - arrow_size * np.cos(angle + np.pi/6),
                               p2.y() - arrow_size * np.sin(angle + np.pi/6))

            path = QPainterPath()
            path.moveTo(p2)
            path.lineTo(p_arrow1)
            path.lineTo(p_arrow2)
            path.closeSubpath()

            painter.setBrush(QBrush(self.draw_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(path)

            offset = arrow_size * 0.5
            p2_adjusted = QPointF(p2.x() - offset * np.cos(angle),
                                  p2.y() - offset * np.sin(angle))

            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(p1, p2_adjusted)
        painter.end()

    def paint_on_pixmap(self, tool, p1, p2, final=True):
        painter = QPainter(self.current_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self.draw_color, self.draw_size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        if tool == "pen":
            painter.drawLine(p1, p2)
        painter.end()

    def handle_text_input(self, pos):
        text, ok = QInputDialog.getText(self, "Add Text", "Enter text:")
        if ok and text:
            self.push_undo()
            painter = QPainter(self.current_pixmap)
            painter.setPen(QColor(self.draw_color))
            font = QFont("Arial", self.text_font_size)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(pos, text)
            painter.end()
            self.image_item.setPixmap(self.current_pixmap)

    def refresh_temp_item_rect(self, rect):
        if self.temp_item:
            self.scene.removeItem(self.temp_item)
            self.temp_item = None

        if self.current_tool == "rect":
            self.temp_item = self.scene.addRect(rect, QPen(self.draw_color, self.draw_size), QBrush())
        elif self.current_tool == "circle":
            self.temp_item = self.scene.addEllipse(rect, QPen(self.draw_color, self.draw_size), QBrush())
        elif self.current_tool == "polygon":
            cx, cy = rect.center().x(), rect.center().y()
            rx, ry = rect.width()/2, rect.height()/2
            radius = min(rx, ry)
            points = calculate_ngon_points(cx, cy, radius, self.poly_sides)
            if points:
                qpoly = QPolygonF([QPointF(x, y) for x, y in points])
                self.temp_item = self.scene.addPolygon(qpoly, QPen(self.draw_color, 1, Qt.PenStyle.DashLine), QBrush())
        elif self.current_tool in ["blur", "pixelate"]:
            self.temp_item = self.scene.addRect(rect, QPen(Qt.GlobalColor.white, 2, Qt.PenStyle.DashLine), QBrush(QColor(255, 255, 255, 50)))

    def refresh_temp_item_arrow(self, current_pos):
        if self.temp_item:
            self.scene.removeItem(self.temp_item)
            self.temp_item = None

        path = QPainterPath()
        path.moveTo(self.start_point)
        path.lineTo(current_pos)

        line = QPointF(current_pos.x() - self.start_point.x(), current_pos.y() - self.start_point.y())
        angle = np.arctan2(line.y(), line.x())
        arrow_size = self.draw_size * 3
        p_arrow1 = QPointF(current_pos.x() - arrow_size * np.cos(angle - np.pi/6),
                           current_pos.y() - arrow_size * np.sin(angle - np.pi/6))
        p_arrow2 = QPointF(current_pos.x() - arrow_size * np.cos(angle + np.pi/6),
                           current_pos.y() - arrow_size * np.sin(angle + np.pi/6))
        path.moveTo(current_pos)
        path.lineTo(p_arrow1)
        path.moveTo(current_pos)
        path.lineTo(p_arrow2)

        self.temp_item = self.scene.addPath(path, QPen(self.draw_color, self.draw_size))

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Close Editor', 'Are you sure you want to discard changes?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.closed_signal.emit()
            event.accept()
        else:
            event.ignore()
