from re import A
from widgets.utils import *

from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPixmap, QPainter, QImage, QCursor, QPen, QBrush
from PyQt5.QtCore import QPoint, Qt, QSize

import cv2
import numpy as np


class ListPoints:
    def __init__(self):
        self.selected_point = -1
        self.search_area = 6
        self.points = [QPoint(200, 200), QPoint(400, 200), QPoint(400, 400), QPoint(200, 400)]

    def update_location(self, loc):
        if self.selected_point >= 0:
            self.points[self.selected_point] = QPoint(int(loc.x()), int(loc.y()))

    def pairs(self):
        return [(self.points[0], self.points[1]), (self.points[1], self.points[2]),
                (self.points[2], self.points[3]), (self.points[3], self.points[0]),
        ]

    def check_select_pos(self, loc):
        for i, p in enumerate(self.points):
            if self.in_the_area(p, loc, e=self.search_area):
                self.selected_point = i
                return True
        return False

    def released(self):
        self.selected_point = -1

    def get_points(self):
        min_x, max_x, min_y, max_y = 9999, 0, 9999, 0

        for p in self.points:
            if max_x < p.x():
                max_x = p.x()
            
            if min_x > p.x():
                min_x = p.x()

            if max_y < p.y():
                max_y = p.y()
            
            if min_y > p.y():
                min_y = p.y()

        return np.float32([[p.x(), p.y()] for p in self.points]), max_y - min_y, max_x - min_x

    @staticmethod
    def in_the_area(p, loc, e):
        return abs(p.x() - loc.x()) < e and abs(p.y() - loc.y()) < e


class Canvas(QWidget):
    zoom_request = QtCore.pyqtSignal(int, QtCore.QPoint)
    scroll_request = QtCore.pyqtSignal(int, int)
    location_request = QtCore.pyqtSignal(int, int)

    NONE_MODE, BRUSH_MODE, ERASER_MODE = 0, 1, 2
    DRAWING_MODE, SPLITTING_MODE = 0, 1

    def __init__(self, brush_size, dirty_callback):
        super().__init__()

        self.points = ListPoints()

        self.image = None
        self.pixmap = None
        self.mask_pixmap = None
        self.splitting_pixmap = None
        self.painter = QPainter()
        self.cursor = CURSOR_DEFAULT
        
        self.drawing_mode = self.NONE_MODE
        self.app_mode = self.DRAWING_MODE
        self.cursor_pos = QPoint(0, 0)

        self.drawing = False

        self.update_brush_size(brush_size)
        self.last_point = QPoint()

        self.scale = 1.0
        self.offsets = QPoint(), QPoint()

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.WheelFocus)

        self.dirty_callback = dirty_callback

    def update_cursor(self):
        if self.pixmap:
            self.cursor = CURSOR_DRAW
        else:
            self.cursor = CURSOR_DEFAULT

    def change2brush(self):
        if self.pixmap:
            self.drawing_mode = self.BRUSH_MODE
        else:
            self.drawing_mode = self.NONE_MODE
            
    def change2eraser(self):
        if self.pixmap:
            self.drawing_mode = self.ERASER_MODE
        else:
            self.drawing_mode = self.NONE_MODE

    def wheelEvent(self, ev):
        mods, delta = ev.modifiers(), ev.angleDelta()
        if Qt.ControlModifier == int(mods):
            self.zoom_request.emit(delta.y(), ev.pos())
        else:
            self.scroll_request.emit(delta.x(), Qt.Horizontal)
            self.scroll_request.emit(delta.y(), Qt.Vertical)
        ev.accept()

    def paintEvent(self, event):
        if not self.pixmap:
            return super().paintEvent(event)
        
        self.painter.begin(self)

        self.painter.setRenderHint(QPainter.Antialiasing)
        self.painter.setRenderHint(QPainter.HighQualityAntialiasing)
        self.painter.setRenderHint(QPainter.SmoothPixmapTransform)

        self.painter.scale(self.scale, self.scale)

        if self.app_mode == self.DRAWING_MODE:
            self.drawing_mode_painter_event()
        else:
            self.splitting_mode_painter_event()

        self.painter.end()

    def drawing_mode_painter_event(self):
        self.painter.drawPixmap(0, 0, self.join_pixmap())

        if self.drawing_mode != self.NONE_MODE:
            x, y = int(self.cursor_pos.x()), int(self.cursor_pos.y())

            p = QPen(Qt.white, 1, Qt.SolidLine)
            p.setCosmetic(True)
            self.painter.setPen(p)
            self.painter.drawEllipse(x - self.half_brush_size, y - self.half_brush_size, self.brush_size, self.brush_size)

            p = QPen(Qt.black, 1, Qt.DashLine)
            p.setCosmetic(True)
            self.painter.setPen(p)
            self.painter.drawEllipse(x - self.half_brush_size, y - self.half_brush_size, self.brush_size, self.brush_size)

    def splitting_mode_painter_event(self):
        list_pairs = self.points.pairs()

        self.painter.drawPixmap(0, 0, self.pixmap)

        pen = QPen(Qt.red, 3, Qt.SolidLine)
        pen.setCosmetic(True)
        self.painter.setPen(pen)

        for pairs in list_pairs:
            self.painter.drawLine(pairs[0], pairs[1])
        
        pen = QPen(Qt.blue, 6, Qt.SolidLine)
        pen.setCosmetic(True)

        brush = QBrush(Qt.blue, Qt.SolidPattern)
        self.painter.setPen(pen)
        self.painter.setBrush(brush)

        for pairs in list_pairs:
            self.painter.drawEllipse(pairs[0].x() - 3, pairs[0].y() - 3, 6, 6)
            self.painter.drawEllipse(pairs[1].x() - 3, pairs[1].y() - 3, 6, 6)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.last_point = self.transform_position(event.localPos())
            self.drawing = True

            if self.app_mode == self.SPLITTING_MODE:
                self.points.check_select_pos(self.last_point)

    def mouseReleaseEvent(self, event):
        if event.button == Qt.LeftButton:
            self.drawing = False

        if self.app_mode == self.SPLITTING_MODE:
            self.points.released()

    def mouseMoveEvent(self, ev):
        self.cursor_pos = self.transform_position(ev.localPos())
        self.location_request.emit(int(self.cursor_pos.x()), int(self.cursor_pos.y()))

        if self.app_mode == self.DRAWING_MODE:
            self.drawing_mode_mouse_move_event(ev)
        else:
            self.splitting_mode_mouse_move_event(ev)

        self.update()

    def drawing_mode_mouse_move_event(self, ev):
        if ev.buttons() == Qt.LeftButton and self.drawing and self.drawing_mode != self.NONE_MODE:
            self.dirty_callback()

            color = Qt.green if self.drawing_mode == self.BRUSH_MODE else Qt.white

            painter = QPainter(self.mask_pixmap)
            painter.setPen(QPen(color, self.brush_size, Qt.SolidLine, join=Qt.RoundJoin))
            painter.drawLine(self.last_point, self.cursor_pos)
            self.last_point = self.cursor_pos

    def splitting_mode_mouse_move_event(self, ev):
        if self.points.selected_point >= 0 and not self.out_of_pixmap(self.cursor_pos):
            self.points.update_location(self.cursor_pos)

    def enterEvent(self, ev):
        self.overrideCursor(self.cursor)

    def out_of_pixmap(self, p):
        w, h = self.pixmap.width(), self.pixmap.height()
        return not (0 <= p.x() <= w - 1 and 0 <= p.y() <= h - 1)

    def leaveEvent(self, ev):
        if self.app_mode == self.SPLITTING_MODE:
            self.points.released()

        self.drawing = False
        self.restore_cursor()

    def update_image(self, image):
        self.image = image
        self.update()
        self.update_cursor()

    def loadPixmap(self, image, pixmap, mask_pixmap, clear_shapes=True):
        self.image = image
        self.pixmap = pixmap
        self.mask_pixmap = mask_pixmap

        splitting_qimage = QImage(QSize(self.image.shape[1], self.image.shape[0]), QImage.Format_RGB888)
        splitting_qimage.fill(Qt.white)
        self.splitting_pixmap = QPixmap.fromImage(splitting_qimage)

        self.update()
        self.update_cursor()

    def update_app_mode(self, app_mode):
        self.app_mode = app_mode
        self.update()
        self.update_cursor()

    def update_brush_size(self, new_brush_size):
        self.brush_size = new_brush_size
        self.half_brush_size = self.brush_size // 2

    def reset_state(self):
        self.restore_cursor()
        self.image = None
        self.pixmap = None
        self.mask_pixmap = None
        self.splitting_pixmap = None
        self.update()
        self.update_cursor()

    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        if self.pixmap:
            return self.scale * self.pixmap.size()
        return super(Canvas, self).minimumSizeHint()

    def transform_position(self, point):
        return point / self.scale

    def overrideCursor(self, cursor):
        self.restore_cursor()
        self.cursor = cursor
        QApplication.setOverrideCursor(cursor)

    def restore_cursor(self):
        QApplication.restoreOverrideCursor()

    def image2qpixmap(self, image):
        height, width, _ = image.shape
        bytesPerLine = 3 * width
        return QPixmap.fromImage(QImage(image.data, width, height, bytesPerLine, QImage.Format_RGB888))

    def qpixmap2image(self, pixmap):
        qimage = pixmap.toImage()
        return self.qimage2image(qimage)

    def qimage2image(self, qimage):
        width = qimage.width()
        height = qimage.height()

        ptr = qimage.bits()
        ptr.setsize(height * width * 4)
        arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
        return cv2.cvtColor(arr[:, :, :3], cv2.COLOR_BGR2RGB)

    def join_pixmap(self):
        if self.app_mode == self.DRAWING_MODE:
            mask = self.qpixmap2image(self.mask_pixmap)
            dst = cv2.addWeighted(self.image, 0.8, mask, 0.2, 0)
        else:
            mask = self.qpixmap2image(self.splitting_pixmap)
            dst = cv2.addWeighted(self.image, 0.45, mask, 0.55, 0)
        return self.image2qpixmap(dst)