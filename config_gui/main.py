"""
Main ROI Configurator application.
"""
import sys
import os
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QGroupBox, QPushButton,
    QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from .models import ROIConfig, ROIData
from .widgets import ImageViewer, ROIPropertiesWidget
from utils.logger import get_logger

logger = get_logger(__name__)


class ROIConfigurator(QMainWindow):
    """Main ROI configurator window."""
    def __init__(self, config_path: Optional[str] = None):
        super().__init__()
        self.config = ROIConfig(config_path)
        self.current_roi = None

        self.setup_ui()
        self.setup_menu()
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
        main_layout = QHBoxLayout()

        # Left panel - Image viewer
        self.image_viewer = ImageViewer()
        main_layout.addWidget(self.image_viewer, 3)

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

        main_layout.addWidget(right_panel, 1)

        central_widget.setLayout(main_layout)

        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

        # Connect signals
        self.add_btn.clicked.connect(self.add_roi)
        self.edit_btn.clicked.connect(self.edit_roi)
        self.delete_btn.clicked.connect(self.delete_roi)
        self.image_viewer.roi_selected.connect(self.on_new_roi_selected)

        self.update_roi_list()

    def setup_menu(self):
        """Setup menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('File')
        open_action = QAction('Open Config', self)
        save_action = QAction('Save Config', self)
        exit_action = QAction('Exit', self)

        open_action.triggered.connect(self.open_config)
        save_action.triggered.connect(self.save_config)
        exit_action.triggered.connect(self.close)

        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

    def update_title(self):
        """Update window title with config path."""
        title = "ROI Configurator"
        if self.config.config_path:
            title += f" - {os.path.basename(self.config.config_path)}"
        self.setWindowTitle(title)

    def load_image_from_config(self):
        """Try to load an image from the config's video source."""
        # For now, use test image
        test_image = "test_frame.jpg"
        if os.path.exists(test_image):
            self.image_viewer.load_image(test_image)
            self.image_viewer.clear_rois()
            for roi in self.config.rois:
                self.image_viewer.add_roi(roi)
            self.status_bar.showMessage("Loaded test frame", 3000)
        else:
            self.status_bar.showMessage("No test frame available", 3000)

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

    def on_new_roi_selected(self, roi):
        """Handle new ROI created by selection."""
        # Auto-generate ID
        roi.id = f"ROI_{len(self.config.rois) + 1}"
        roi.label = roi.id
        roi.vehicle = None
        roi.measurement_unit = ""

        self.config.rois.append(roi)
        self.update_roi_list()
        self.properties_widget.set_roi(roi)
        self.current_roi = roi

        # Select the new item
        for i in range(self.roi_list.count()):
            item = self.roi_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == roi:
                self.roi_list.setCurrentItem(item)
                break

    def on_properties_changed(self, roi):
        """Handle ROI properties changes."""
        self.update_roi_list()
        self.image_viewer.clear_rois()
        for r in self.config.rois:
            self.image_viewer.add_roi(r)

    def add_roi(self):
        """Add new ROI."""
        roi = ROIData()
        roi.id = f"ROI_{len(self.config.rois) + 1}"
        roi.label = roi.id
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
            self.image_viewer.clear_rois()
            for r in self.config.rois:
                self.image_viewer.add_roi(r)

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

    sys.exit(app.exec())


if __name__ == "__main__":
    main()