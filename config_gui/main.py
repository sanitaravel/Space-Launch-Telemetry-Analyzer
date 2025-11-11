"""
Main ROI Configurator application.
"""
import sys
import os
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QGroupBox, QPushButton,
    QMessageBox, QFileDialog, QSlider, QLabel, QComboBox
)
from PyQt6.QtGui import QActionGroup
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QShortcut, QKeySequence

from .models import ROIConfig, ROIData
from .widgets import VideoWidget, ROIPropertiesWidget
from utils.logger import get_logger
import cv2
import os
from pathlib import Path

logger = get_logger(__name__)


class ROIConfigurator(QMainWindow):
    """Main ROI configurator window."""
    def __init__(self, config_path: Optional[str] = None):
        super().__init__()
        self.config = ROIConfig(config_path)
        self.current_roi = None

        self.setup_ui()
        self.setup_menu()
        self.setup_shortcuts()
        self.update_title()

        if config_path:
            self.load_image_from_config()

    def setup_ui(self):
        """Setup the main UI."""
        self.setWindowTitle("ROI Configurator")
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout()

        # Video area with controls
        video_layout = QVBoxLayout()

        # Video widget
        self.video_widget = VideoWidget()
        self.video_widget.set_mode('select')
        video_layout.addWidget(self.video_widget, 1)

        # Timeline slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self.seek_to_frame)
        video_layout.addWidget(self.slider)

        # Time and frame labels
        time_frame_layout = QHBoxLayout()
        self.time_label = QLabel("Time: 00:00:00")
        self.frame_label = QLabel("Frame: 0")
        time_frame_layout.addWidget(self.time_label)
        time_frame_layout.addStretch()
        time_frame_layout.addWidget(self.frame_label)
        video_layout.addLayout(time_frame_layout)

        # Control buttons
        controls_layout = QHBoxLayout()
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.play_pause)
        controls_layout.addWidget(self.play_btn)

        self.step_back_btn = QPushButton("<<")
        self.step_back_btn.clicked.connect(self.step_back)
        controls_layout.addWidget(self.step_back_btn)

        self.step_forward_btn = QPushButton(">>")
        self.step_forward_btn.clicked.connect(self.step_forward)
        controls_layout.addWidget(self.step_forward_btn)

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "1x", "2x", "4x", "8x", "16x", "32x", "64x"])
        self.speed_combo.setCurrentText("1x")
        self.speed_combo.currentTextChanged.connect(self.change_speed)
        controls_layout.addWidget(self.speed_combo)

        video_layout.addLayout(controls_layout)

        # Right panel - ROI management
        right_panel = QWidget()
        right_layout = QVBoxLayout()

        # ROI list
        list_group = QGroupBox("ROIs")
        list_layout = QVBoxLayout()

        self.roi_list = QListWidget()
        self.roi_list.itemClicked.connect(self.on_roi_selected)

        button_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.edit_btn = QPushButton("Edit")
        self.delete_btn = QPushButton("Delete")
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)

        list_layout.addWidget(self.roi_list)
        list_layout.addLayout(button_layout)
        list_group.setLayout(list_layout)

        # Properties
        self.properties_widget = ROIPropertiesWidget()
        self.properties_widget.properties_changed.connect(self.on_properties_changed)

        right_layout.addWidget(list_group, 1)
        right_layout.addWidget(self.properties_widget, 1)
        right_panel.setLayout(right_layout)

        # Main layout: video on left, controls in middle, right panel on right
        content_layout = QHBoxLayout()
        content_layout.addLayout(video_layout, 2)
        content_layout.addWidget(right_panel, 1)

        main_layout.addLayout(content_layout)

        central_widget.setLayout(main_layout)

        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

        # Video playback
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame)
        self.playing = False
        self.frame_idx = 0
        self.total_frames = 0
        self.fps = 30.0
        self.speed = 1.0

        # Connect signals
        self.add_btn.clicked.connect(self.add_roi)
        self.edit_btn.clicked.connect(self.edit_roi)
        self.delete_btn.clicked.connect(self.delete_roi)
        self.video_widget.roi_selected.connect(self.on_new_roi_selected)
        self.properties_widget.properties_changed.connect(self.on_properties_changed)
        self.properties_widget.engine_group_selected.connect(self.video_widget.set_current_engine_group)
        self.video_widget.point_added.connect(self.on_point_added)

        self.update_roi_list()

    def setup_menu(self):
        """Setup menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('File')
        save_action = QAction('Save Config', self)
        exit_action = QAction('Exit', self)

        save_action.triggered.connect(self.save_config)
        exit_action.triggered.connect(self.close)

        file_menu.addAction(save_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu('View')
        self.select_action = QAction('Select ROI', self)
        self.select_action.setCheckable(True)
        self.select_action.setChecked(True)
        self.zoom_action = QAction('Zoom and Pan', self)
        self.zoom_action.setCheckable(True)
        self.reset_zoom_action = QAction('Reset Zoom and Pan', self)
        view_menu.addAction(self.select_action)
        view_menu.addAction(self.zoom_action)
        view_menu.addSeparator()
        view_menu.addAction(self.reset_zoom_action)

        # Group them
        self.mode_group = QActionGroup(self)
        self.mode_group.addAction(self.select_action)
        self.mode_group.addAction(self.zoom_action)

        self.select_action.triggered.connect(lambda: self.set_mode('select'))
        self.zoom_action.triggered.connect(lambda: self.set_mode('zoom'))
        self.reset_zoom_action.triggered.connect(self.reset_zoom)

        # Help menu
        help_menu = menubar.addMenu('Help')
        hotkeys_action = QAction('Keyboard Shortcuts', self)
        about_action = QAction('About GUI Components', self)

        hotkeys_action.triggered.connect(self.show_hotkeys_help)
        about_action.triggered.connect(self.show_gui_components_help)

        help_menu.addAction(hotkeys_action)
        help_menu.addAction(about_action)

    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Ctrl+S: Save config
        self.save_shortcut = QShortcut(QKeySequence.StandardKey.Save, self)
        self.save_shortcut.activated.connect(self.save_config)

        # Space: Play/Pause toggle
        self.play_pause_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.play_pause_shortcut.activated.connect(self.play_pause)

        # Left/Right arrows: Frame stepping
        self.step_back_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.step_back_shortcut.activated.connect(self.step_back)

        self.step_forward_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        self.step_forward_shortcut.activated.connect(self.step_forward)

        # Ctrl+A: Add new ROI
        self.add_roi_shortcut = QShortcut(QKeySequence("Ctrl+A"), self)
        self.add_roi_shortcut.activated.connect(self.add_roi)

        # Delete: Delete selected ROI
        self.delete_roi_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        self.delete_roi_shortcut.activated.connect(self.delete_roi)

        # Ctrl+Z: Toggle zoom/pan mode
        self.toggle_zoom_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.toggle_zoom_shortcut.activated.connect(self.toggle_zoom_mode)

        # Ctrl+R: Reset zoom and pan
        self.reset_zoom_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self.reset_zoom_shortcut.activated.connect(self.reset_zoom)

        # Ctrl+T: Set start time/frame to current position
        self.set_start_now_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        self.set_start_now_shortcut.activated.connect(self.set_start_to_current)

        # Ctrl+E: Set end time/frame to current position
        self.set_end_now_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
        self.set_end_now_shortcut.activated.connect(self.set_end_to_current)

        # Up/Down arrows: Navigate ROI list
        self.roi_up_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Up), self)
        self.roi_up_shortcut.activated.connect(self.navigate_roi_up)

        self.roi_down_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Down), self)
        self.roi_down_shortcut.activated.connect(self.navigate_roi_down)

        # Speed selection: 1-9 keys
        self.speed_1_shortcut = QShortcut(QKeySequence(Qt.Key.Key_1), self)
        self.speed_1_shortcut.activated.connect(lambda: self.set_speed_by_index(0))  # 0.25x

        self.speed_2_shortcut = QShortcut(QKeySequence(Qt.Key.Key_2), self)
        self.speed_2_shortcut.activated.connect(lambda: self.set_speed_by_index(1))  # 0.5x

        self.speed_3_shortcut = QShortcut(QKeySequence(Qt.Key.Key_3), self)
        self.speed_3_shortcut.activated.connect(lambda: self.set_speed_by_index(2))  # 1x

        self.speed_4_shortcut = QShortcut(QKeySequence(Qt.Key.Key_4), self)
        self.speed_4_shortcut.activated.connect(lambda: self.set_speed_by_index(3))  # 2x

        self.speed_5_shortcut = QShortcut(QKeySequence(Qt.Key.Key_5), self)
        self.speed_5_shortcut.activated.connect(lambda: self.set_speed_by_index(4))  # 4x

        self.speed_6_shortcut = QShortcut(QKeySequence(Qt.Key.Key_6), self)
        self.speed_6_shortcut.activated.connect(lambda: self.set_speed_by_index(5))  # 8x

        self.speed_7_shortcut = QShortcut(QKeySequence(Qt.Key.Key_7), self)
        self.speed_7_shortcut.activated.connect(lambda: self.set_speed_by_index(6))  # 16x

        self.speed_8_shortcut = QShortcut(QKeySequence(Qt.Key.Key_8), self)
        self.speed_8_shortcut.activated.connect(lambda: self.set_speed_by_index(7))  # 32x

        self.speed_9_shortcut = QShortcut(QKeySequence(Qt.Key.Key_9), self)
        self.speed_9_shortcut.activated.connect(lambda: self.set_speed_by_index(8))  # 64x

        # ROI navigation: [ and ] jump to start/end of selected ROI
        self.roi_start_shortcut = QShortcut(QKeySequence(Qt.Key.Key_BracketLeft), self)
        self.roi_start_shortcut.activated.connect(self.jump_to_roi_start)

        self.roi_end_shortcut = QShortcut(QKeySequence(Qt.Key.Key_BracketRight), self)
        self.roi_end_shortcut.activated.connect(self.jump_to_roi_end)

    def toggle_zoom_mode(self):
        """Toggle between select and zoom modes."""
        if self.video_widget.mode == 'select':
            self.set_mode('zoom')
            self.zoom_action.setChecked(True)
        else:
            self.set_mode('select')
            self.select_action.setChecked(True)

    def set_start_to_current(self):
        """Set start time/frame to current position."""
        if self.current_roi:
            self.properties_widget.on_start_now()

    def set_end_to_current(self):
        """Set end time/frame to current position."""
        if self.current_roi:
            self.properties_widget.on_end_now()

    def navigate_roi_up(self):
        """Navigate to previous ROI in the list."""
        current_row = self.roi_list.currentRow()
        if current_row > 0:
            self.roi_list.setCurrentRow(current_row - 1)
            # Trigger selection
            item = self.roi_list.currentItem()
            if item:
                self.on_roi_selected(item)

    def navigate_roi_down(self):
        """Navigate to next ROI in the list."""
        current_row = self.roi_list.currentRow()
        if current_row < self.roi_list.count() - 1:
            self.roi_list.setCurrentRow(current_row + 1)
            # Trigger selection
            item = self.roi_list.currentItem()
            if item:
                self.on_roi_selected(item)

    def set_speed_by_index(self, index: int):
        """Set playback speed by combo box index."""
        if 0 <= index < self.speed_combo.count():
            self.speed_combo.setCurrentIndex(index)
            # The change_speed method will be called automatically due to the signal connection

    def jump_to_roi_start(self):
        """Jump to the start frame/time of the currently selected ROI."""
        if self.current_roi and self.current_roi.start_time is not None:
            target_frame = int(self.current_roi.start_time)
            self.seek_to_frame(target_frame)

    def jump_to_roi_end(self):
        """Jump to the end frame/time of the currently selected ROI."""
        if self.current_roi and self.current_roi.end_time is not None:
            target_frame = int(self.current_roi.end_time)
            self.seek_to_frame(target_frame)

    def reset_zoom(self):
        """Reset zoom to fit the image."""
        self.video_widget.reset_zoom()

    def show_hotkeys_help(self):
        """Show keyboard shortcuts help dialog."""
        hotkeys_text = """
<b>Keyboard Shortcuts</b><br><br>

<b>File Operations:</b><br>
• Ctrl+S: Save configuration<br>
• Ctrl+Q: Quit application<br><br>

<b>Video Playback:</b><br>
• Space: Play/Pause toggle<br>
• Left Arrow: Step backward one frame<br>
• Right Arrow: Step forward one frame<br>
• 1: 0.25x speed, 2: 0.5x speed, 3: 1x speed<br>
• 4: 2x speed, 5: 4x speed, 6: 8x speed<br>
• 7: 16x speed, 8: 32x speed, 9: 64x speed<br><br>

<b>ROI Management:</b><br>
• Ctrl+A: Add new ROI<br>
• Delete: Delete selected ROI<br>
• Up Arrow: Navigate to previous ROI<br>
• Down Arrow: Navigate to next ROI<br>
• [: Jump to start of selected ROI<br>
• ]: Jump to end of selected ROI<br><br>

<b>Time Settings:</b><br>
• Ctrl+T: Set start time/frame to current position<br>
• Ctrl+E: Set end time/frame to current position<br><br>

<b>View Controls:</b><br>
• Ctrl+Z: Toggle zoom/pan mode<br>
• Ctrl+R: Reset zoom and pan to fit<br><br>

<b>Mouse Controls:</b><br>
• Left Click + Drag: Select ROI (in select mode) or pan (in zoom mode)<br>
• Mouse Wheel: Zoom in/out (in zoom mode)<br>
• Right Click: Context menu (future feature)
        """

        QMessageBox.about(self, "Keyboard Shortcuts", hotkeys_text)

    def show_gui_components_help(self):
        """Show GUI components help dialog."""
        components_text = """
<b>GUI Components Guide</b><br><br>

<b>Main Video Area:</b><br>
• Displays the video frames with ROI overlays<br>
• Shows colored rectangles for each ROI<br>
• Supports zoom and pan when in zoom mode<br>
• Click and drag to create new ROIs in select mode<br><br>

<b>Video Controls:</b><br>
• Play/Pause: Start or stop video playback<br>
• Step buttons: Move forward/backward one frame<br>
• Timeline slider: Jump to specific frame<br>
• Speed combo: Change playback speed<br>
• Time/Frame labels: Current position display<br><br>

<b>ROI List Panel:</b><br>
• Shows all configured ROIs<br>
• Format: "ID: Label (vehicle)"<br>
• Click to select and edit ROI<br>
• Add/Edit/Delete buttons for ROI management<br><br>

<b>Properties Panel:</b><br>
• Basic Properties: ID, Label, Vehicle, Measurement Unit<br>
• Time Settings: Start/End frames with "Now" buttons<br>
• Geometry: Rectangle coordinates (X, Y, Width, Height)<br>
• For engines: Point-based geometry with groups<br><br>

<b>Status Bar:</b><br>
• Shows current status messages<br>
• Displays loading progress and error messages<br><br>

<b>Menu Bar:</b><br>
• File: Save configuration, Exit<br>
• View: Select ROI mode, Zoom mode, Reset zoom<br>
• Help: This guide and keyboard shortcuts<br><br>

<b>Interaction Modes:</b><br>
• Select ROI: Click and drag to create/select ROIs<br>
• Zoom and Pan: Mouse wheel to zoom, drag to pan<br>
• Toggle between modes with Ctrl+Z or View menu
        """

        QMessageBox.about(self, "GUI Components Guide", components_text)

    def set_mode(self, mode):
        """Set the interaction mode for the video widget."""
        self.video_widget.set_mode(mode)

    def update_title(self):
        """Update window title with config path."""
        title = "ROI Configurator"
        if self.config.config_path:
            title += f" - {os.path.basename(self.config.config_path)}"
        self.setWindowTitle(title)

    def load_image_from_config(self):
        """Try to load video from the config's video source."""
        if not self.config.config_path:
            self.status_bar.showMessage("No config loaded", 3000)
            return

        # Parse config path to find video
        config_path = Path(self.config.config_path)
        # config path like configs/provider/rocket/flight_number_rois.json
        parts = config_path.parts
        if len(parts) >= 4 and parts[0] == 'configs':
            provider = parts[1]
            rocket = parts[2]
            filename = parts[3]
            # Extract flight_identifier from filename, e.g., flight_123_rois.json -> flight_123
            flight_identifier = filename.replace('_rois.json', '')

            video_dir = Path('flight_recordings') / provider / rocket
            if video_dir.exists():
                # Look for video file
                for ext in ['mp4', 'avi', 'mkv', 'webm']:
                    video_file = video_dir / f"{flight_identifier}.{ext}"
                    if video_file.exists():
                        self.load_video(str(video_file))
                        return

        self.status_bar.showMessage("No video found for config", 3000)

    def load_video(self, video_path):
        """Load video for playback."""
        self.cap = cv2.VideoCapture(video_path)
        if self.cap.isOpened():
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.frame_idx = 0
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if ret:
                self.video_widget.set_frame(frame)
                self.video_widget.frame_idx = 0
                self.video_widget.fps = self.fps
                self.video_widget.time_unit = self.config.time_unit
                self.video_widget.set_rois([roi.__dict__ for roi in self.config.rois])
                # Set slider
                if self.total_frames > 0:
                    self.slider.setMaximum(self.total_frames - 1)
                else:
                    self.slider.setMaximum(0)
                self.slider.setValue(0)
                self.update_time_label()
                self.properties_widget.set_current_frame_info(0, self.fps, self.config.time_unit)
                self.status_bar.showMessage(f"Loaded video: {os.path.basename(video_path)}", 3000)
                # Fit the video to the widget
                self.video_widget.reset_zoom()
            else:
                self.status_bar.showMessage("Failed to read first frame", 3000)
        else:
            self.status_bar.showMessage("Failed to open video", 3000)

    def update_roi_list(self):
        """Update the ROI list widget."""
        self.roi_list.clear()
        for roi in self.config.rois:
            vehicle = roi.vehicle if roi.vehicle else "global"
            item_text = f"{roi.id}: {roi.label} ({vehicle})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, roi)
            self.roi_list.addItem(item)

    def on_roi_selected(self, item):
        """Handle ROI selection from list."""
        roi = item.data(Qt.ItemDataRole.UserRole)
        self.properties_widget.set_roi(roi)
        self.current_roi = roi
        self.video_widget.set_current_roi(roi.__dict__)

    def on_new_roi_selected(self, roi):
        """Handle new ROI created by selection."""
        # Auto-generate ID
        roi.id = f"ROI_{len(self.config.rois) + 1}"
        roi.label = roi.id
        roi.vehicle = None
        roi.measurement_unit = ""

        # Set default start and end times to cover the entire video
        if self.total_frames > 0:
            if self.config.time_unit == "frames":
                roi.start_time = 0
                roi.end_time = self.total_frames - 1
            elif self.config.time_unit in ("seconds", "s"):
                roi.start_time = 0.0
                roi.end_time = (self.total_frames - 1) / self.fps
            else:
                # Default to frames if unknown unit
                roi.start_time = 0
                roi.end_time = self.total_frames - 1
        else:
            # No video loaded, set to None
            roi.start_time = None
            roi.end_time = None

        self.config.rois.append(roi)
        self.update_roi_list()
        self.properties_widget.set_roi(roi)
        self.current_roi = roi
        self.video_widget.set_current_roi(roi.__dict__)

        # Select the new item
        for i in range(self.roi_list.count()):
            item = self.roi_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == roi:
                self.roi_list.setCurrentItem(item)
                break

    def on_properties_changed(self, roi):
        """Handle ROI properties changes."""
        self.update_roi_list()
        self.video_widget.set_rois([r.__dict__ for r in self.config.rois])

    def on_point_added(self):
        """Handle point added to engine group."""
        # Update the properties widget to refresh the points list
        if self.current_roi:
            self.properties_widget.set_roi(self.current_roi)
        # Update video display
        self.video_widget.set_rois([r.__dict__ for r in self.config.rois])

    def add_roi(self):
        """Add new ROI."""
        roi = ROIData()
        roi.id = f"ROI_{len(self.config.rois) + 1}"
        roi.label = roi.id

        # Set default start and end times to cover the entire video
        if self.total_frames > 0:
            if self.config.time_unit == "frames":
                roi.start_time = 0
                roi.end_time = self.total_frames - 1
            elif self.config.time_unit in ("seconds", "s"):
                roi.start_time = 0.0
                roi.end_time = (self.total_frames - 1) / self.fps
            else:
                # Default to frames if unknown unit
                roi.start_time = 0
                roi.end_time = self.total_frames - 1
        else:
            # No video loaded, set to None
            roi.start_time = None
            roi.end_time = None

        self.config.rois.append(roi)
        self.update_roi_list()

    def edit_roi(self):
        """Edit selected ROI."""
        current_item = self.roi_list.currentItem()
        if current_item:
            roi = current_item.data(Qt.ItemDataRole.UserRole)
            self.properties_widget.set_roi(roi)
            self.current_roi = roi

    def delete_roi(self):
        """Delete selected ROI."""
        current_item = self.roi_list.currentItem()
        if current_item:
            roi = current_item.data(Qt.ItemDataRole.UserRole)
            self.config.rois.remove(roi)
            self.update_roi_list()
            self.video_widget.set_rois([r.__dict__ for r in self.config.rois])

    def open_config(self):
        """Open config file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open ROI Config", "", "JSON files (*.json)"
        )
        if file_path:
            self.config = ROIConfig(file_path)
            self.update_title()
            self.update_roi_list()
            self.load_image_from_config()

    def update_time_label(self):
        time_sec = self.frame_idx / self.fps
        minutes = int(time_sec // 60)
        seconds = int(time_sec % 60)
        self.time_label.setText(f"Time: {minutes:02d}:{seconds:02d}")
        self.frame_label.setText(f"Frame: {self.frame_idx}")

    def change_speed(self):
        text = self.speed_combo.currentText()
        self.speed = float(text[:-1])
        if self.playing:
            interval = int(1000 / (self.fps * self.speed))
            self.timer.setInterval(interval)

    def seek_to_frame(self, value):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, value)
            ret, frame = self.cap.read()
            if ret:
                self.frame_idx = value
                self.video_widget.frame_idx = value
                self.video_widget.set_frame(frame)
                self.update_time_label()
                self.properties_widget.set_current_frame_info(self.frame_idx, self.fps, self.config.time_unit)

    def play_pause(self):
        if self.playing:
            self.timer.stop()
            self.play_btn.setText("Play")
        else:
            interval = int(1000 / (self.fps * self.speed))
            self.timer.start(interval)
            self.play_btn.setText("Pause")
        self.playing = not self.playing

    def next_frame(self):
        if self.cap:
            ret, frame = self.cap.read()
            if ret:
                self.frame_idx += 1
                self.video_widget.frame_idx = self.frame_idx
                self.video_widget.set_frame(frame)
                self.slider.blockSignals(True)
                self.slider.setValue(self.frame_idx)
                self.slider.blockSignals(False)
                self.update_time_label()
                self.properties_widget.set_current_frame_info(self.frame_idx, self.fps, self.config.time_unit)
            else:
                self.timer.stop()
                self.playing = False
                self.play_btn.setText("Play")

    def step_back(self):
        if self.cap and self.frame_idx > 0:
            self.frame_idx -= 1
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_idx)
            ret, frame = self.cap.read()
            if ret:
                self.video_widget.frame_idx = self.frame_idx
                self.video_widget.set_frame(frame)
                self.slider.blockSignals(True)
                self.slider.setValue(self.frame_idx)
                self.slider.blockSignals(False)
                self.update_time_label()
                self.properties_widget.set_current_frame_info(self.frame_idx, self.fps, self.config.time_unit)

    def step_forward(self):
        """Step forward by one frame."""
        if self.cap:
            # Calculate next frame index
            next_idx = self.frame_idx + 1
            if self.total_frames and next_idx >= self.total_frames:
                return
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, next_idx)
            ret, frame = self.cap.read()
            if ret:
                self.frame_idx = next_idx
                self.video_widget.frame_idx = self.frame_idx
                self.video_widget.set_frame(frame)
                self.slider.blockSignals(True)
                self.slider.setValue(self.frame_idx)
                self.slider.blockSignals(False)
                self.update_time_label()
                self.properties_widget.set_current_frame_info(self.frame_idx, self.fps, self.config.time_unit)

    def save_config(self):
        """Save config file."""
        if not self.config.config_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save ROI Config", "", "JSON files (*.json)"
            )
            if not file_path:
                return
            self.config.config_path = file_path

        if self.config.save_config():
            self.status_bar.showMessage("Config saved successfully", 3000)
            self.update_title()
        else:
            self.status_bar.showMessage("Failed to save config", 3000)


def main():
    """Main entry point for the GUI."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Get config path from command line or show dialog
    config_path = None
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    window = ROIConfigurator(config_path)
    window.show()

    # Don't exit the process when GUI closes, so CLI can continue
    app.exec()
    # sys.exit(app.exec())  # Removed to allow returning to CLI


if __name__ == "__main__":
    main()