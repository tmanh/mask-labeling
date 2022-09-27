import functools
import os
import cv2
import math
import natsort

import numpy as np
import os.path as osp

from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon, QImage, QPixmap, QImageReader
from PyQt5.QtCore import Qt, QSize, QCoreApplication
from widgets.brightness_contrast_dialog import BrightnessContrastDialog

from PIL import Image
from widgets.brushsize import BrushDialog

from widgets.canvas import *
from widgets.file_dialog_preview import FileDialogPreview
from widgets.output_widget import OutputBlock
from widgets.zoom_widget import ZoomWidget
from widgets.toolbar import LabelingToolBar

from utils.basic import __appname__, fmtShortcut


class LabelData:
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = 0, 1, 2

    def __init__(self, image_path, mask_path):
        self.load_images(image_path, mask_path)
        self.load_qimages()

    def load_qimages(self):
        height, width = self.image.shape[:2]

        self.qimage = self.to_qimage(self.image, height, width)
        self.qmask = self.to_qimage(self.mask, height, width)

    def load_images(self, image_path, mask_path):
        self.image_path = image_path
        self.mask_path = mask_path

        self.image = cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2RGB)
        
        self.load_mask(mask_path)

    def load_mask(self, mask_path):
        self.height, self.width = self.image.shape[:2]
        if osp.exists(mask_path):
            self.mask = cv2.cvtColor(cv2.imread(mask_path), cv2.COLOR_BGR2RGB)
        else:
            self.mask = np.ones_like(self.image) * 255

    def to_qimage(self, image, height, width):
        bytes_per_line = 3 * width
        return QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)

    def is_null(self):
        return self.image is None


class MainWindow(QMainWindow):
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = 0, 1, 2
    BRUSH_MODE, ERASER_MODE = 0, 1
    DRAWING_MODE, SPLITTING_MODE = 0, 1

    def __init__(self):
        super(MainWindow, self).__init__()

        self.set_config()
        self.create_actions()
        self.create_menu()
        self.create_widgets()
        self.set_other_settings()
        self.init_toolbar()

    def create_menu(self):
        self.main_menu = self.menuBar()
        self.file_menu = self.main_menu.addMenu('&File')
        self.edit_menu = self.main_menu.addMenu('&Edit')
        self.image_menu = self.main_menu.addMenu('Drawing && &Image')

        self.recent_file_menu = QMenu('&Recent files')

        self.image_menu.addAction(self.brush_size_action)
        self.image_menu.addAction(self.brightness_contrast_action)

        self.file_menu.addAction(self.open_action)
        self.file_menu.addAction(self.opendir_action)
        self.file_menu.addAction(self.save_action)
        self.file_menu.addAction(self.exit_action)
        self.file_menu.addMenu(self.recent_file_menu)

        self.edit_menu.addAction(self.fit_window_action)
        self.edit_menu.addAction(self.fit_width_action)
        self.edit_menu.addAction(self.zoom_in_action)
        self.edit_menu.addAction(self.zoom_out_action)
        self.edit_menu.addAction(self.zoom_original_action)

    def create_actions(self):
        self.open_action = QAction(QIcon('./icons/open.png'), '&Open', self)        
        self.open_action.setShortcut('Ctrl+O')
        self.open_action.setStatusTip('Open')
        self.open_action.triggered.connect(self.open_call)

        self.opendir_action = QAction(QIcon('./icons/opened-folder.png'), 'Open &Dir', self)        
        self.opendir_action.setShortcut('Ctrl+D')
        self.opendir_action.setStatusTip('Open folder')
        self.opendir_action.triggered.connect(self.opendir_call)

        self.open_next_action = QAction(QIcon('./icons/next.png'), '&Next Image', self)        
        self.open_next_action.setShortcut('Ctrl+Right')
        self.open_next_action.setStatusTip('Open the next image')
        self.open_next_action.setEnabled(False)
        self.open_next_action.triggered.connect(self.open_next_call)

        self.open_prev_action = QAction(QIcon('./icons/prev.png'), '&Prev Image', self)        
        self.open_prev_action.setShortcut('Ctrl+Left')
        self.open_prev_action.setStatusTip('Open the previous image')
        self.open_prev_action.setEnabled(False)
        self.open_prev_action.triggered.connect(self.open_prev_call)

        self.save_action = QAction(QIcon('./icons/save.png'), '&Save', self)        
        self.save_action.setShortcut('Ctrl+S')
        self.save_action.setStatusTip('Save mask')
        self.save_action.setEnabled(False)
        self.save_action.triggered.connect(self.save_file_call)

        self.exit_action = QAction(QIcon('./icons/exit.png'), '&Exit', self)        
        self.exit_action.setShortcut('Ctrl+Q')
        self.exit_action.setStatusTip('Exit application')
        self.exit_action.triggered.connect(self.exit_call)

        self.brush_size_action = QAction(QIcon('./icons/brush_size.png'), 'Brush size', self)
        self.brush_size_action.triggered.connect(self.brush_size_call)

        self.brush_action = QAction(QIcon('./icons/brush.png'), 'Brush', self)
        self.brush_action.triggered.connect(self.update_brush)

        self.app_mode_action = QAction(QIcon('./icons/drawing.png'), 'Drawing', self)
        self.app_mode_action.triggered.connect(self.update_app_mode)

        self.split_action = QAction(QIcon('./icons/split.png'), 'Split', self)
        self.split_action.triggered.connect(self.split_images)

        self.fit_window_action = QAction(QIcon('./icons/fit-to-page.png'), '&Fit Window', self)
        self.fit_window_action.setCheckable(True)
        self.fit_window_action.setEnabled(False)
        self.fit_window_action.setWhatsThis('Zoom follows window size')
        self.fit_window_action.triggered.connect(self.set_fit_window)

        self.fit_width_action = QAction(QIcon('./icons/fit-width.png'), '&Fit &Width', self)
        self.fit_width_action.setCheckable(True)
        self.fit_width_action.setEnabled(False)
        self.fit_width_action.setWhatsThis('Zoom follows window width')
        self.fit_width_action.triggered.connect(self.set_fit_width)

        self.zoom_in_action = QAction(QIcon('./icons/zoom-in.png'), 'Zoom &In', self)
        self.zoom_in_action.setWhatsThis('Increase zoom level')
        self.zoom_in_action.setEnabled(False)
        self.zoom_in_action.triggered.connect(functools.partial(self.add_zoom, 1.1))

        self.zoom_out_action = QAction(QIcon('./icons/zoom-out.png'), '&Zoom Out', self)
        self.zoom_out_action.setWhatsThis('Decrease zoom level')
        self.zoom_out_action.setEnabled(False)
        self.zoom_out_action.triggered.connect(functools.partial(self.add_zoom, 0.9))

        self.zoom_original_action = QAction(QIcon('./icons/zoom-to-actual-size.png'), '&Original size', self)
        self.zoom_original_action.setWhatsThis('Zoom to original size')
        self.zoom_original_action.setEnabled(False)
        self.zoom_original_action.triggered.connect(functools.partial(self.set_zoom, 100))

        self.brightness_contrast_action = QAction(QIcon('./icons/brightness.png'), 'Brightness &&\n&Contrast', self)
        self.brightness_contrast_action.setWhatsThis('Modify the brightness/contrast of the image')
        self.brightness_contrast_action.setEnabled(False)
        self.brightness_contrast_action.triggered.connect(self.modify_brightness_contrast)

    def create_widgets(self):
        self.file_list_widget = QListWidget()
        self.file_list_widget.itemSelectionChanged.connect(self.file_selection_changed)

        self.canvas = Canvas(self.brush_size, self.set_dirty)

        self.zoom_action = QWidgetAction(self)
        self.zoom_widget = ZoomWidget()
        self.zoom_action.setDefaultWidget(self.zoom_widget)
        self.zoom_widget.setWhatsThis(
            str(
                self.tr(
                    "Zoom in or out of the image. Also accessible with "
                    "{} and {} from the canvas."
                )
            ).format(
                fmtShortcut(
                    "{},{}".format('Ctrl++', 'Ctrl+-')  # zoom in, zoom out
                ),
                fmtShortcut(self.tr("Ctrl+Wheel")),
            )
        )
        self.zoom_widget.setEnabled(False)
        self.zoom_widget.valueChanged.connect(self.paint_canvas)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.canvas)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_bars = {
            Qt.Vertical: self.scroll_area.verticalScrollBar(),
            Qt.Horizontal: self.scroll_area.horizontalScrollBar(),
        }
        self.canvas.scroll_request.connect(self.scroll_request)
        self.canvas.zoom_request.connect(self.zoom_request)
        self.canvas.location_request.connect(self.mouse_move_in_canvas)
            
        self.setCentralWidget(self.scroll_area)

        self.file_search = QLineEdit()
        self.file_search.setPlaceholderText(self.tr("Search Filename"))
        self.file_search.textChanged.connect(self.file_search_changed)
        self.file_list_widget = QListWidget()
        self.file_list_widget.itemSelectionChanged.connect(self.file_selection_changed)

        self.file_list_layout = QVBoxLayout()
        self.file_list_layout.setContentsMargins(0, 0, 0, 0)
        self.file_list_layout.setSpacing(0)
        self.file_list_layout.addWidget(self.file_search)
        self.file_list_layout.addWidget(self.file_list_widget)
        
        self.file_dock = QDockWidget(self.tr("File List"), self)
        self.file_dock.setObjectName("Files")
        
        self._file_list_widget = QListWidget()
        self._file_list_widget.setLayout(self.file_list_layout)
        self.file_dock.setWidget(self._file_list_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.file_dock)

        self.output_block = OutputBlock(osp.abspath(self.mask_dir), osp.abspath(self.split_dir),
                                        self.mask_dir_callback, self.split_dir_callback, self)
        self.output_block_dock = QDockWidget(self.tr("Output Directories"), self)
        self.output_block_dock.setWidget(self.output_block)
        self.addDockWidget(Qt.TopDockWidgetArea, self.output_block_dock)

    def set_config(self):
        self.filename = ''
        self.mask_file = ''
        self.image_path = None
        self.image_data = None
        self.mask_dir = './mask'
        self.split_dir = './split'
        self.dirty = False

        self.max_recent_files = 10
        self.recent_files = []
        self.last_opendir = None

        self.brush_size = 10
        self.drawing_mode = self.BRUSH_MODE
        self.app_mode = self.DRAWING_MODE

        self.setWindowTitle(__appname__)
        self.setMinimumSize(QSize(800, 600))

        self.statusBar().showMessage(str(self.tr("%s started.")) % __appname__)
        self.statusBar().show()

    def set_other_settings(self):
        self.zoom_values = {}                                       # key=filename, value=(zoom_mode, zoom_value)
        self.scroll_values = {Qt.Horizontal: {}, Qt.Vertical: {}}   # key=filename, value=scroll_value

        self.zoom_level = 100
        self.zoom_mode = self.FIT_WINDOW
        self.fit_window_action.setChecked(Qt.Checked)
        self.scalers = {
            self.FIT_WINDOW: self.scale_fit_window,
            self.FIT_WIDTH: self.scale_fit_width,
            self.MANUAL_ZOOM: lambda: 1,
        }

        self.list_file_actions = (
            self.open_action,
            self.opendir_action,
            self.open_next_action,
            self.open_prev_action,
            self.save_action,
        )

        self.list_zoom_actions = (
            self.zoom_widget,
            self.zoom_in_action,
            self.zoom_out_action,
            self.zoom_original_action,
            self.fit_width_action,
            self.fit_window_action,
        )

        self.list_drawing_actions = (
            self.brush_action,
            self.app_mode_action,
            self.brush_size_action,
            self.brightness_contrast_action,
            self.split_action,
        )

        self.brightness_contrast_values = {}

    def init_toolbar(self):
        self.toolbar = LabelingToolBar('ToolBar')
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        
        for action in self.list_file_actions:
            if isinstance(action, QAction):
                self.toolbar.addAction(action)

        self.toolbar.addSeparator()

        for action in self.list_zoom_actions:
            if isinstance(action, QAction):
                self.toolbar.addAction(action)

        self.toolbar.addSeparator()

        for action in self.list_drawing_actions:
            if isinstance(action, QAction):
                self.toolbar.addAction(action)

        self.addToolBar(Qt.LeftToolBarArea, self.toolbar)

    @property
    def image_list(self):
        lst = []
        for i in range(self.file_list_widget.count()):
            item = self.file_list_widget.item(i)
            lst.append(item.text())
        return lst

    def brush_size_call(self):
        dialog = BrushDialog(self.brush_size, self.on_new_brush_size, parent=self)
        dialog.exec_()

    def update_brush(self):
        self.drawing_mode = 1 - self.drawing_mode
        if self.drawing_mode == self.BRUSH_MODE:
            self.brush_action.setIcon(QIcon('./icons/brush.png'))
            self.brush_action.setText('Brush')
        else:
            self.brush_action.setIcon(QIcon('./icons/eraser.png'))
            self.brush_action.setText('Eraser')
        self.update_drawing_mode()

    def update_drawing_mode(self):
        if self.drawing_mode == self.BRUSH_MODE:
            self.canvas.drawing_mode = self.canvas.BRUSH_MODE
        else:
            self.canvas.drawing_mode = self.canvas.ERASER_MODE
        self.canvas.update()

    def update_app_mode(self):
        self.app_mode = 1 - self.app_mode
        if self.app_mode == self.DRAWING_MODE:
            self.app_mode_action.setIcon(QIcon('./icons/drawing.png'))
            self.app_mode_action.setText('Draw Mode')
            self.canvas.update_app_mode(self.canvas.DRAWING_MODE)
        else:
            self.app_mode_action.setIcon(QIcon('./icons/irregular-quadrilateral.png'))
            self.app_mode_action.setText('Split Mode')
            self.canvas.update_app_mode(self.canvas.SPLITTING_MODE)

    def split_images(self):
        if self.app_mode == self.DRAWING_MODE:
            if self.split_dir and not osp.exists(osp.join(self.split_dir, 'defect')):
                os.mkdir(osp.join(self.split_dir, 'defect'))

            if self.split_dir and not osp.exists(osp.join(self.split_dir, 'normal')):
                os.mkdir(osp.join(self.split_dir, 'normal'))

            base_file = osp.basename(self.filename).split('.')[0]

            image = cv2.cvtColor(self.image_data.image, cv2.COLOR_RGB2BGR)
            mask = cv2.cvtColor(self.canvas.qpixmap2image(self.canvas.mask_pixmap), cv2.COLOR_RGB2BGR)

            height, width = image.shape[:2]
            
            patch_size = self.output_block.size_spinbox.value()
            half_patch_size = patch_size // 2
            rotation_range = int(math.ceil(patch_size / math.sqrt(2))) + 1
            step = self.output_block.stride_spinbox.value()
            for i in range(0, height, step):
                for j in range(0, width, step):
                    y = i + half_patch_size
                    x = j + half_patch_size
                    str_y = f'{y}'.zfill(4)
                    str_x = f'{x}'.zfill(4)

                    patch = image[i:i+patch_size, j:j+patch_size]
                    mask_patch = mask[i:i+patch_size, j:j+patch_size]
                    itype = 'defect' if (mask_patch[:, :, 0] == 0).any() else 'normal'
                    split_file = osp.join(self.split_dir, f'{itype}/{base_file}-{str_y}-{str_x}-000.png')
                    cv2.imwrite(split_file, patch)

                    """
                    if rotation_range < y < height - rotation_range - 1 and rotation_range < x < width - rotation_range - 1:
                        istart = i + half_patch_size - rotation_range
                        iend = i + half_patch_size + rotation_range
                        jstart = j + half_patch_size - rotation_range
                        jend = j + half_patch_size + rotation_range

                        mask_patch = mask[i:i+patch_size, j:j+patch_size]
                        angle = 15 if (mask_patch[:, :, 0] == 0).any() else 60

                        rot_patch = image[istart:iend,jstart:jend]
                        rot_mask_patch = mask[istart:iend,jstart:jend]
                        for k in range(0, 360, angle):
                            str_k = f'{k}'.zfill(3)
                            rot_mat = cv2.getRotationMatrix2D((rotation_range, rotation_range), k, 1.0)

                            rotated = cv2.warpAffine(src=rot_patch, M=rot_mat, dsize=(2 * rotation_range, 2 * rotation_range))
                            rotated_mask = cv2.warpAffine(src=rot_mask_patch, M=rot_mat, dsize=(2 * rotation_range, 2 * rotation_range))

                            patch = rotated[rotation_range-half_patch_size:rotation_range+half_patch_size,
                                            rotation_range-half_patch_size:rotation_range+half_patch_size]

                            mask_patch = rotated_mask[rotation_range-half_patch_size:rotation_range+half_patch_size,
                                                      rotation_range-half_patch_size:rotation_range+half_patch_size]

                            itype = 'defect' if (mask_patch[:, :, 0] == 0).any() else 'normal'
                            split_file = osp.join(self.split_dir, f'{itype}/{base_file}-{str_y}-{str_x}-{str_k}.png')

                            cv2.imwrite(split_file, patch)
                    else:
                        patch = image[i:i+patch_size, j:j+patch_size]
                        rot90 = cv2.rotate(patch, cv2.ROTATE_90_CLOCKWISE)
                        rot180 = cv2.rotate(patch, cv2.ROTATE_180)
                        rot270 = cv2.rotate(patch, cv2.ROTATE_90_COUNTERCLOCKWISE)

                        mask_patch = mask[i:i+patch_size, j:j+patch_size]
                        mask_rot90 = cv2.rotate(mask_patch, cv2.ROTATE_90_CLOCKWISE)
                        mask_rot180 = cv2.rotate(mask_patch, cv2.ROTATE_180)
                        mask_rot270 = cv2.rotate(mask_patch, cv2.ROTATE_90_COUNTERCLOCKWISE)

                        itype = 'defect' if (mask_patch[:, :, 0] == 0).any() else 'normal'
                        split_file = osp.join(self.split_dir, f'{itype}/{base_file}-{str_y}-{str_x}-000.png')
                        cv2.imwrite(split_file, patch)

                        itype = 'defect' if (mask_rot270[:, :, 0] == 0).any() else 'normal'
                        split_file = osp.join(self.split_dir, f'{itype}/{base_file}-{str_y}-{str_x}-090.png')
                        cv2.imwrite(split_file, rot90)

                        itype = 'defect' if (mask_rot180[:, :, 0] == 0).any() else 'normal'
                        split_file = osp.join(self.split_dir, f'{itype}/{base_file}-{str_y}-{str_x}-180.png')
                        cv2.imwrite(split_file, rot180)

                        itype = 'defect' if (mask_rot270[:, :, 0] == 0).any() else 'normal'
                        split_file = osp.join(self.split_dir, f'{itype}/{base_file}-{str_y}-{str_x}-270.png')
                        cv2.imwrite(split_file, rot270)
                    """
        else:
            pts1, height, width = self.canvas.points.get_points()
            pts2 = np.float32([[0, 0],[width, 0], [height, width],[0, height]])
            transform = cv2.getPerspectiveTransform(pts1, pts2)

            dst = cv2.warpPerspective(self.image_data.image, transform, (height, width))
            dst = cv2.cvtColor(dst, cv2.COLOR_RGB2BGR)

            split_file = f'{osp.splitext(self.filename)[0]}.png'
            if self.split_dir and osp.exists(self.split_dir):
                split_file_without_path = osp.basename(split_file)
                split_file = osp.join(self.split_dir, split_file_without_path)

            cv2.imwrite(split_file, dst)

    def on_new_brush_size(self, brush_size):
        self.brush_size = brush_size
        self.canvas.update_brush_size(self.brush_size)

    def opendir_call(self, _value=False, dirpath=None):
        if not self.may_continue():
            return

        default_opendir_path = self.get_default_opendir_path(dirpath)

        dir_path = str(
            QFileDialog.getExistingDirectory(
                self,
                self.tr("%s - Open Directory") % __appname__,
                default_opendir_path,
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
            )
        )
        self.import_dir_images(dir_path)

    def open_next_call(self, _value=False, load=True):
        if not self.may_continue():
            return

        if len(self.image_list) <= 0:
            return

        filename = None
        if self.filename is None:
            filename = self.image_list[0]
        else:
            curr_index = self.image_list.index(self.filename)
            if curr_index + 1 < len(self.image_list):
                filename = self.image_list[curr_index + 1]
            else:
                filename = self.image_list[-1]
        self.filename = filename

        if self.filename and load:
            self.load_file(self.filename)

    def open_prev_call(self):
        if not self.may_continue():
            return

        if len(self.image_list) <= 0:
            return

        if self.filename is None:
            return

        curr_index = self.image_list.index(self.filename)
        if curr_index - 1 >= 0:
            filename = self.image_list[curr_index - 1]
            if filename:
                self.load_file(filename)

    def get_default_opendir_path(self, dirpath):
        default_opendir_path = dirpath if dirpath else "."
        if self.last_opendir and osp.exists(self.last_opendir):
            default_opendir_path = self.last_opendir
        else:
            default_opendir_path = osp.dirname(self.filename) if self.filename else "."

        return default_opendir_path

    def modify_brightness_contrast(self):
        # set brightness contrast values
        dialog = BrightnessContrastDialog(Image.fromarray(self.image_data.image), self.on_new_brightness_contrast, parent=self)
        brightness, contrast = self.brightness_contrast_values.get(self.filename, (None, None))

        if brightness is not None:
            dialog.slider_brightness.setValue(brightness)
            dialog.original_brightness = int(brightness)
        if contrast is not None:
            dialog.slider_contrast.setValue(contrast)
            dialog.original_contrast = int(contrast)
        dialog.exec_()

        brightness = dialog.slider_brightness.value()
        contrast = dialog.slider_contrast.value()

        self.brightness_contrast_values[self.filename] = (brightness, contrast)

    def mouse_move_in_canvas(self, x, y):
        self.status(f'({x}, {y})')

    def scroll_request(self, delta, orientation):
        units = -delta * 0.1  # natural scroll
        bar = self.scroll_bars[orientation]
        value = bar.value() + bar.singleStep() * units
        self.set_scroll(orientation, int(value))

    def set_scroll(self, orientation, value):
        self.scroll_bars[orientation].setValue(value)
        self.scroll_values[orientation][self.filename] = value

    def set_zoom(self, value):
        self.fit_width_action.setChecked(False)
        self.fit_window_action.setChecked(False)
        self.zoom_mode = self.MANUAL_ZOOM
        self.zoom_widget.setValue(value)
        self.zoom_values[self.filename] = (self.zoom_mode, value)

    def add_zoom(self, increment=1.1):
        zoom_value = self.zoom_widget.value() * increment
        if increment > 1:
            zoom_value = math.ceil(zoom_value)
        else:
            zoom_value = math.floor(zoom_value)
        self.set_zoom(zoom_value)

    def zoom_request(self, delta, pos):
        canvas_width_old = self.canvas.width()
        units = 1.1
        if delta < 0:
            units = 0.9
        self.add_zoom(units)

        canvas_width_new = self.canvas.width()
        if canvas_width_old != canvas_width_new:
            canvas_scale_factor = canvas_width_new / canvas_width_old

            x_shift = round(pos.x() * canvas_scale_factor) - pos.x()
            y_shift = round(pos.y() * canvas_scale_factor) - pos.y()

            self.set_scroll(
                Qt.Horizontal,
                self.scroll_bars[Qt.Horizontal].value() + x_shift,
            )
            self.set_scroll(
                Qt.Vertical,
                self.scroll_bars[Qt.Vertical].value() + y_shift,
            )

    def open_call(self):
        if not self.may_continue():
            return

        path = osp.dirname(str(self.filename)) if self.filename else "."
        formats = self.supported_image_formats()
        filters = f'Image & Label files {formats}'
        
        fileDialog = FileDialogPreview(self)
        fileDialog.setFileMode(FileDialogPreview.ExistingFile)
        fileDialog.setNameFilter(filters)
        fileDialog.setWindowTitle('{__appname__} - Choose Image or Label file')
        fileDialog.setWindowFilePath(path)
        fileDialog.setViewMode(FileDialogPreview.Detail)
        
        if fileDialog.exec_():
            filename = fileDialog.selectedFiles()[0]
            if filename:
                self.load_file(filename)

    def mask_dir_callback(self, mask_dir):
        if len(self.mask_file) > 0:
            self.mask_file = self.mask_file.replace(self.mask_dir, mask_dir)
        self.mask_dir = mask_dir

    def split_dir_callback(self, split_dir):
        self.split_dir = split_dir

    def resizeEvent(self, event):
        if self.canvas and (self.image_data and not self.image_data.is_null()) and self.zoom_mode != self.MANUAL_ZOOM:
            self.adjust_scale()
        super(MainWindow, self).resizeEvent(event)

    def toggle_actions(self, value=True):
        for z in self.list_zoom_actions:
            z.setEnabled(value)

        self.brightness_contrast_action.setEnabled(value)

    def on_new_brightness_contrast(self, image):
        self.canvas.update_image(image)

    def load_file(self, filename):
        filename = str(filename)
        if filename in self.image_list and (
            self.file_list_widget.currentRow() != self.image_list.index(filename)
        ):
            self.file_list_widget.setCurrentRow(self.image_list.index(filename))
            self.file_list_widget.repaint()
            return

        self.reset_state()
        self.canvas.setEnabled(False)

        if not QtCore.QFile.exists(filename):
            self.errorMessage(
                self.tr('Error opening file'),
                self.tr('No such file: <b>%s</b>') % filename,
            )
            return False
        
        # assumes same name, but json extension
        self.status(f'Loading {osp.basename(str(filename))}...')

        self.mask_file = self.create_mask_path(filename)
        
        self.filename = filename
        self.image_data = LabelData(filename, self.mask_file)
    
        if self.image_data.is_null():
            self.errorMessage(
                self.tr("Error opening file"),
                self.tr(
                    "<p>Make sure <i>{0}</i> is a valid image file.<br/>"
                    "Supported image formats: {1}</p>"
                ).format(filename, self.supported_image_formats()),
            )
            self.status(self.tr("Error reading %s") % filename)
            return False

        self.canvas.loadPixmap(self.image_data.image, QPixmap.fromImage(self.image_data.qimage),
                               QPixmap.fromImage(self.image_data.qmask))

        self.set_clean()
        self.canvas.setEnabled(True)
        self.update_drawing_mode()

        is_initial_load = not self.zoom_values
        if self.filename in self.zoom_values:
            self.zoom_mode = self.zoom_values[self.filename][0]
            self.set_zoom(self.zoom_values[self.filename][1])
        elif is_initial_load:
            self.adjust_scale(initial=True)

        for orientation in self.scroll_values:
            if self.filename in self.scroll_values[orientation]:
                self.set_scroll(orientation, self.scroll_values[orientation][self.filename])

        self.paint_canvas()
        self.add_recent_file(self.filename)
        self.toggle_actions(True)

        self.canvas.setFocus()
        self.status(str(self.tr("Loaded %s")) % osp.basename(str(filename)))
        return True

    def paint_canvas(self):
        assert not self.image_data.is_null(), "cannot paint null image"
        self.canvas.scale = 0.01 * self.zoom_widget.value()
        self.canvas.adjustSize()
        self.canvas.update()

    def create_mask_path(self, filename):
        mask_file = f'{osp.splitext(filename)[0]}-m.png'
        if self.mask_dir:
            mask_file_without_path = osp.basename(mask_file)
            mask_file = osp.join(self.mask_dir, mask_file_without_path)
        return mask_file

    def file_search_changed(self):
        self.import_dir_images(
            self.last_opendir,
            pattern=self.file_search.text(),
            load=False,
        )

    def file_selection_changed(self):
        items = self.file_list_widget.selectedItems()
        if not items:
            return
        item = items[0]

        if not self.may_continue():
            return

        curr_index = self.image_list.index(str(item.text()))
        if curr_index < len(self.image_list):
            filename = self.image_list[curr_index]
            if filename:
                self.load_file(filename)

    def save_file_call(self):
        mask = self.canvas.qpixmap2image(self.canvas.mask_pixmap)
        cv2.imwrite(self.mask_file, mask)
        self.set_clean()

    def exit_call(self):
        QCoreApplication.quit()

    def may_continue(self):
        if not self.dirty:
            return True

        msg = f'Do you want to save your work to \"{self.filename}\" before closing?\nAny unsaved work will be lost.'
        title = 'Save annotations?'

        answer = QMessageBox.question(self, title, msg, QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        
        if answer == QMessageBox.Discard:
            return True
        elif answer == QMessageBox.Save:
            self.save_file_call()
            return True
        else:
            return False

    def set_fit_window(self, value=True):
        if value:
            self.fit_width_action.setChecked(False)
        self.zoom_mode = self.FIT_WINDOW if value else self.MANUAL_ZOOM
        self.adjust_scale()

    def set_fit_width(self, value=True):
        if value:
            self.fit_window_action.setChecked(False)
        self.zoom_mode = self.FIT_WIDTH if value else self.MANUAL_ZOOM
        self.adjust_scale()

    def set_title_with_filename(self):
        title = __appname__
        if self.filename is not None:
            title = "{} - {}".format(title, self.filename)
        self.setWindowTitle(title)

    def adjust_scale(self, initial=False):
        value = self.scalers[self.FIT_WINDOW if initial else self.zoom_mode]()
        value = int(100 * value)
        self.zoom_widget.setValue(value)
        self.zoom_values[self.filename] = (self.zoom_mode, value)

    def scale_fit_window(self):
        e = 2.0  # So that no scrollbars are generated.
        w1 = self.centralWidget().width() - e
        h1 = self.centralWidget().height() - e
        a1 = w1 / h1

        # Calculate a new scale value based on the pixmap's aspect ratio.
        w2 = self.image_data.width
        h2 = self.image_data.height
        a2 = w2 / h2
        return w1 / w2 if a2 >= a1 else h1 / h2

    def scale_fit_width(self):
        w = self.centralWidget().width() - 2.0
        return w / self.canvas.pixmap.width()

    def set_clean(self):
        self.dirty = False
        self.save_action.setEnabled(False)
        self.set_title_with_filename()

    def set_dirty(self):
        self.dirty = True
        self.save_action.setEnabled(True)
        self.set_title_with_filename()

    def add_recent_file(self, filename):
        if filename in self.recent_files:
            self.recent_files.remove(filename)
        elif len(self.recent_files) >= self.max_recent_files:
            self.recent_files.pop()
        self.recent_files.insert(0, filename)

    def import_dir_images(self, dirpath, pattern=None, load=True):
        self.open_next_action.setEnabled(True)
        self.open_prev_action.setEnabled(True)

        if not self.may_continue() or not dirpath:
            return

        self.last_opendir = dirpath
        self.filename = None
        self.file_list_widget.clear()
        for filename in self.scan_all_images(dirpath):
            if pattern and pattern not in filename:
                continue
            item = QListWidgetItem(filename)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.file_list_widget.addItem(item)
        self.open_next_call(load=load)

    def scan_all_images(self, path):
        extensions = [
            ".%s" % fmt.data().decode().lower()
            for fmt in QImageReader.supportedImageFormats()
        ]

        images = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.lower().endswith(tuple(extensions)):
                    relativePath = osp.join(root, file)
                    images.append(relativePath)
        images = natsort.os_sorted(images)
        return images

    def reset_state(self):
        self.filename = None
        self.image_path = None
        self.image_data = None
        self.label_file = None
        self.other_data = None
        self.canvas.reset_state()

    def status(self, message, delay=5000):
        self.statusBar().showMessage(message, delay)

    @staticmethod
    def supported_image_formats():
        image_formats = [f'*.{fmt.data().decode()}' for fmt in QImageReader.supportedImageFormats()]

        return ' '.join(image_formats)
