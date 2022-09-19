from widgets.utils import *

from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPixmap, QPainter, QImage, QCursor, QPen
from PyQt5.QtCore import QPoint, Qt

import cv2
import numpy as np


class Canvas(QWidget):
    zoom_request = QtCore.pyqtSignal(int, QtCore.QPoint)
    scroll_request = QtCore.pyqtSignal(int, int)
    location_request = QtCore.pyqtSignal(int, int)

    NONE_MODE, BRUSH_MODE, ERASER_MODE = 0, 1, 2

    def __init__(self, brush_size, dirty_callback):
        super().__init__()

        self.image = None
        self.pixmap = None
        self.mask_pixmap = None
        self.painter = QPainter()
        self.cursor = CURSOR_DEFAULT
        
        self.drawing_mode = self.NONE_MODE
        self.cursor_pos = QPoint(0, 0)

        self.drawing = False

        self.brush_size = brush_size
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

        self.painter.drawPixmap(0, 0, self.join_pixmap())

        if self.drawing_mode != self.NONE_MODE:
            x, y = int(self.cursor_pos.x()), int(self.cursor_pos.y())
            p = QPen(Qt.white, 1, Qt.SolidLine)
            p.setCosmetic(True)
            self.painter.setPen(p)
            self.painter.drawEllipse(x - 5//2, y - 5//2, 5, 5)

            p = QPen(Qt.black, 1, Qt.DashLine)
            p.setCosmetic(True)
            self.painter.setPen(p)
            self.painter.drawEllipse(x - 5//2, y - 5//2, 5, 5)

        self.painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.last_point = self.transform_position(event.localPos())
            self.drawing = True

    def mouseReleaseEvent(self, event):
        if event.button == Qt.LeftButton:
            self.drawing = False

    def mouseMoveEvent(self, ev):
        self.cursor_pos = self.transform_position(ev.localPos())
        self.location_request.emit(int(self.cursor_pos.x()), int(self.cursor_pos.y()))

        if ev.buttons() == Qt.LeftButton and self.drawing and self.drawing_mode != self.NONE_MODE:
            self.dirty_callback()

            color = Qt.green if self.drawing_mode == self.BRUSH_MODE else Qt.white

            painter = QPainter(self.mask_pixmap)
            painter.setPen(QPen(color, self.brush_size, Qt.SolidLine, join=Qt.RoundJoin))
            painter.drawLine(self.last_point, self.cursor_pos)
            self.last_point = self.cursor_pos

        self.update()

    def enterEvent(self, ev):
        self.overrideCursor(self.cursor)

    def update_image(self, image):
        self.image = image
        self.update()
        self.update_cursor()

    def loadPixmap(self, image, pixmap, mask_pixmap, clear_shapes=True):
        self.image = image
        self.pixmap = pixmap
        self.mask_pixmap = mask_pixmap
        self.update()
        self.update_cursor()

    def reset_state(self):
        self.restore_cursor()
        self.image = None
        self.pixmap = None
        self.mask_pixmap = None
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
        mask = self.qpixmap2image(self.mask_pixmap)
        dst = cv2.addWeighted(self.image, 0.8, mask, 0.2, 0)
        return self.image2qpixmap(dst)