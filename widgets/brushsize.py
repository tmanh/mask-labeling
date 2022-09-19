
import numpy as np

from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QSize, QPoint, QRect


class LabeledSlider(QtWidgets.QWidget):
    def __init__(self, minimum, maximum, interval=1, orientation=Qt.Horizontal, labels=None, parent=None):
        super(LabeledSlider, self).__init__(parent=parent)

        levels=range(minimum, maximum+interval, interval)
        if labels is not None:
            if not isinstance(labels, (tuple, list)):
                raise Exception("<labels> is a list or tuple.")
            if len(labels) != len(levels):
                raise Exception("Size of <labels> doesn't match levels.")
            self.levels=list(zip(levels,labels))
        else:
            self.levels=list(zip(levels,map(str,levels)))

        if orientation==Qt.Horizontal:
            self.layout=QtWidgets.QVBoxLayout(self)
        elif orientation==Qt.Vertical:
            self.layout=QtWidgets.QHBoxLayout(self)
        else:
            raise Exception("<orientation> wrong.")

        # gives some space to print labels
        self.left_margin=10
        self.top_margin=10
        self.right_margin=10
        self.bottom_margin=10

        self.layout.setContentsMargins(self.left_margin,self.top_margin, self.right_margin,self.bottom_margin)

        self.slider = QtWidgets.QSlider(orientation, self)
        self.slider.setMinimum(minimum)
        self.slider.setMaximum(maximum)
        self.slider.setValue(minimum)
        if orientation==Qt.Horizontal:
            self.slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
            self.slider.setMinimumWidth(300) # just to make it easier to read
        else:
            self.slider.setTickPosition(QtWidgets.QSlider.TicksLeft)
            self.slider.setMinimumHeight(300) # just to make it easier to read
        self.slider.setTickInterval(interval)
        self.slider.setSingleStep(1)

        self.layout.addWidget(self.slider)

    def paintEvent(self, e):
        super(LabeledSlider,self).paintEvent(e)

        style=self.slider.style()
        painter=QtGui.QPainter(self)
        st_slider=QtWidgets.QStyleOptionSlider()
        st_slider.initFrom(self.slider)
        st_slider.orientation=self.slider.orientation()

        length=style.pixelMetric(QtWidgets.QStyle.PM_SliderLength, st_slider, self.slider)
        available=style.pixelMetric(QtWidgets.QStyle.PM_SliderSpaceAvailable, st_slider, self.slider)

        for v, v_str in self.levels:

            # get the size of the label
            rect=painter.drawText(QRect(), Qt.TextDontPrint, v_str)

            if self.slider.orientation()==Qt.Horizontal:
                # I assume the offset is half the length of slider, therefore
                # + length//2
                x_loc=QtWidgets.QStyle.sliderPositionFromValue(self.slider.minimum(),
                        self.slider.maximum(), v, available)+length//2

                # left bound of the text = center - half of text width + L_margin
                left=x_loc-rect.width()//2+self.left_margin
                bottom=self.rect().bottom()

                # enlarge margins if clipping
                if v==self.slider.minimum():
                    if left<=0:
                        self.left_margin=rect.width()//2-x_loc
                    if self.bottom_margin<=rect.height():
                        self.bottom_margin=rect.height()

                    self.layout.setContentsMargins(self.left_margin,
                            self.top_margin, self.right_margin,
                            self.bottom_margin)

                if v==self.slider.maximum() and rect.width()//2>=self.right_margin:
                    self.right_margin=rect.width()//2
                    self.layout.setContentsMargins(self.left_margin,
                            self.top_margin, self.right_margin,
                            self.bottom_margin)

            else:
                y_loc=QtGui.QStyle.sliderPositionFromValue(self.slider.minimum(),
                        self.slider.maximum(), v, available, upsideDown=True)

                bottom=y_loc+length//2+rect.height()//2+self.top_margin-3
                # there is a 3 px offset that I can't attribute to any metric

                left=self.left_margin-rect.width()
                if left<=0:
                    self.left_margin=rect.width()+2
                    self.layout.setContentsMargins(self.left_margin,
                            self.top_margin, self.right_margin,
                            self.bottom_margin)

            pos=QPoint(left, bottom)
            painter.drawText(pos, v_str)

        return


class BrushDialog(QtWidgets.QDialog):
    def __init__(self, original_brush_size, callback, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Brush size")

        self.original_brush_size = original_brush_size

        self.slider_brush_size = self._create_slider(original_brush_size)

        brush_label = QtWidgets.QLabel('Brush size:')

        self.cancel_button = QtWidgets.QPushButton('Cancel', self)
        self.cancel_button.clicked.connect(self.on_click_cancel)

        self.ok_button = QtWidgets.QPushButton('OK', self)
        self.ok_button.clicked.connect(self.on_click_ok)

        formLayout = QtWidgets.QGridLayout()
        formLayout.addWidget(brush_label, 0, 0)
        formLayout.addWidget(self.slider_brush_size, 0, 1)

        formLayout.addWidget(self.cancel_button, 2, 0)
        formLayout.addWidget(self.ok_button, 2, 1)
        self.setLayout(formLayout)

        self.setFixedSize(QSize(450, 120))

        self.callback = callback

    def on_click_cancel(self):
        self._set_brush_size_value(self.original_brush_size)
        
        self.close()
        
    def on_click_ok(self):
        self.close()

    def on_value_changed(self):
        self.callback(self.slider_brush_size.slider.value())

    def _create_slider(self, value):
        slider = LabeledSlider(1, 20, orientation=Qt.Horizontal)
        slider.tracking = True
        slider.slider.setValue(value)
        slider.slider.valueChanged.connect(self.on_value_changed)
        return slider

    def _set_brush_size_value(self, value):
        self.slider_brush_size.setValue(value)
        self.slider_brush_size.sliderPosition = int(value)
        self.slider_brush_size.update()
        self.slider_brush_size.repaint()
