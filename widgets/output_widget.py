from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5 import QtCore


class OutputBlock(QtWidgets.QWidget):
    def __init__(self, mask_dir, split_dir, mask_dir_callback, split_dir_callback, parent=None):
        super().__init__(parent)

        self.mask_dir_label = QtWidgets.QLabel('Mask Directory:')

        self.mask_dir_combobox = self.createComboBox(mask_dir)
        
        self.open_mask_dir = QtWidgets.QPushButton('Browse...', self)
        self.open_mask_dir.clicked.connect(self.on_click_open_mask_dir)

        self.split_dir_label = QtWidgets.QLabel('Splitted Images Directory:')

        self.split_dir_combobox = self.createComboBox(split_dir)
        
        self.open_split_dir = QtWidgets.QPushButton('Browse...', self)
        self.open_split_dir.clicked.connect(self.on_click_open_split_dir)

        formLayout = QtWidgets.QGridLayout()
        formLayout.addWidget(self.mask_dir_label, 0, 0)
        formLayout.addWidget(self.mask_dir_combobox, 0, 1)
        formLayout.addWidget(self.open_mask_dir, 0, 2)

        formLayout.addWidget(self.split_dir_label, 1, 0)
        formLayout.addWidget(self.split_dir_combobox, 1, 1)
        formLayout.addWidget(self.open_split_dir, 1, 2)
        self.setLayout(formLayout)

        self.mask_dir_callback = mask_dir_callback
        self.split_dir_callback = split_dir_callback
        
    def on_click_open_mask_dir(self):
        dir_path = str(
            QtWidgets.QFileDialog.getExistingDirectory(
                self,
                self.tr("Open Directory"),
                str(self.mask_dir_combobox.currentText()),
                QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks,
            )
        )
        if dir_path:
            self.mask_dir_combobox.setCurrentText(dir_path)
            self.mask_dir_callback(dir_path)

    def on_click_open_split_dir(self):
        dir_path = str(
            QtWidgets.QFileDialog.getExistingDirectory(
                self,
                self.tr("Open Directory"),
                str(self.split_dir_combobox.currentText()),
                QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks,
            )
        )
        if dir_path:
            self.split_dir_combobox.setCurrentText(dir_path)
            self.split_dir_callback(dir_path)

    @staticmethod
    def createComboBox(text):
        comboBox = QtWidgets.QComboBox()
        comboBox.setEditable(True)
        comboBox.addItem(text)
        comboBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        return comboBox