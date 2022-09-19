import json

from PyQt5.QtWidgets import QWidget, QFileDialog, QScrollArea, QVBoxLayout, QLabel
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt


class ScrollAreaPreview(QScrollArea):
    def __init__(self, *args, **kwargs):
        super(ScrollAreaPreview, self).__init__(*args, **kwargs)

        self.setWidgetResizable(True)

        content = QWidget(self)
        self.setWidget(content)

        lay = QVBoxLayout(content)

        self.label = QLabel(content)
        self.label.setWordWrap(True)

        lay.addWidget(self.label)

    def setText(self, text):
        self.label.setText(text)

    def setPixmap(self, pixmap):
        self.label.setPixmap(pixmap)

    def clear(self):
        self.label.clear()


class FileDialogPreview(QFileDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setOption(self.DontUseNativeDialog, True)

        self.label_preview = ScrollAreaPreview(self)
        self.label_preview.setFixedSize(300, 300)
        self.label_preview.setHidden(True)

        box = QVBoxLayout()
        box.addWidget(self.label_preview)
        box.addStretch()

        self.setFixedSize(self.width() + 300, self.height())
        self.layout().addLayout(box, 1, 3, 1, 1)
        self.currentChanged.connect(self.on_change)

    def on_change(self, path):
        if path.lower().endswith(".json"):
            with open(path, "r") as f:
                data = json.load(f)
                self.label_preview.setText(json.dumps(data, indent=4, sort_keys=False))
            self.label_preview.label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            self.label_preview.setHidden(False)
        else:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                self.label_preview.clear()
                self.label_preview.setHidden(True)
            else:
                self.label_preview.setPixmap(
                    pixmap.scaled(self.label_preview.width() - 30, self.label_preview.height() - 30,
                        Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                self.label_preview.label.setAlignment(Qt.AlignCenter)
                self.label_preview.setHidden(False)