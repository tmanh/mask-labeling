
import numpy as np

from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QSize

from PIL import ImageEnhance, Image


class BrightnessContrastDialog(QtWidgets.QDialog):
    def __init__(self, img, callback, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Brightness/Contrast")

        self.original_brightness = 50
        self.original_contrast = 50

        self.slider_brightness = self._create_slider()
        self.slider_contrast = self._create_slider()

        brightness_label = QtWidgets.QLabel('Brightness:')
        contrast_label = QtWidgets.QLabel('Contrast:')

        self.cancel_button = QtWidgets.QPushButton('Cancel', self)
        self.cancel_button.clicked.connect(self.on_click_cancel)

        self.reset_button = QtWidgets.QPushButton('Reset', self)
        self.reset_button.clicked.connect(self.on_click_reset)

        self.ok_button = QtWidgets.QPushButton('OK', self)
        self.ok_button.clicked.connect(self.on_click_ok)

        formLayout = QtWidgets.QGridLayout()
        formLayout.addWidget(brightness_label, 0, 0)
        formLayout.addWidget(self.slider_brightness, 0, 1)

        formLayout.addWidget(contrast_label, 1, 0)
        formLayout.addWidget(self.slider_contrast, 1, 1)

        formLayout.addWidget(self.cancel_button, 2, 0)
        formLayout.addWidget(self.reset_button, 2, 1)
        formLayout.addWidget(self.ok_button, 2, 2)
        self.setLayout(formLayout)

        self.setFixedSize(QSize(290, 120))

        self.img = img
        self.callback = callback

    def on_click_cancel(self):
        self._set_brightness_value(self.original_brightness)
        self._set_contrast_value(self.original_contrast)
        
        self.close()
        
    def on_click_ok(self):
        self.close()

    def on_click_reset(self):
        self._set_brightness_value(50)
        self._set_contrast_value(50)

    def on_value_changed(self):
        brightness = self.slider_brightness.value() / 50.0
        contrast = self.slider_contrast.value() / 50.0

        img = self.img
        img = ImageEnhance.Brightness(img).enhance(brightness)
        img = ImageEnhance.Contrast(img).enhance(contrast)
        
        self.callback(np.array(img))

    def _create_slider(self):
        slider = QtWidgets.QSlider(Qt.Horizontal)
        slider.tracking = True
        slider.setRange(0, 150)
        slider.setValue(50)
        slider.valueChanged.connect(self.on_value_changed)
        return slider

    def _set_brightness_value(self, value):
        self.slider_brightness.setValue(value)
        self.slider_brightness.sliderPosition = int(value)
        self.slider_brightness.update()
        self.slider_brightness.repaint()

    def _set_contrast_value(self, value):
        self.slider_contrast.setValue(value)
        self.slider_contrast.sliderPosition = int(value)
        self.slider_contrast.update()
        self.slider_contrast.repaint()

    @staticmethod
    def img_pil_to_qimage(img_pil):
        img = np.array(img_pil)
        height, width = img.shape[:2]

        bytes_per_line = 3 * width
        return QtGui.QImage(img.data, width, height, bytes_per_line, QtGui.QImage.Format_RGB888)
