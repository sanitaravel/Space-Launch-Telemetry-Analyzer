# ROI Configurator GUI

Interactive PyQt6 GUI for creating and editing ROI (Region of Interest) configurations for the Starship Analyzer.

## File Structure

- `main.py` - Main application window and entry point
- `models.py` - Data models (ROIData, ROIConfig)
- `widgets.py` - UI widgets (ImageViewer, ROIPropertiesWidget, etc.)
- `config_gui_menu.py` - CLI menu integration
- `config_creator.py` - CLI config creation utilities

## Features

- **Visual ROI Selection**: Click and drag to select rectangular regions on video frames
- **ROI Management**: Add, edit, delete, and organize ROIs
- **Properties Editor**: Configure ROI labels, vehicle assignments, measurement units, and coordinates
- **Config File Integration**: Load and save ROI configurations in JSON format

## Usage

### From CLI Menu

1. Run the main application
2. Select "Config GUI" > "Launch Interactive ROI Configurator (GUI)"
3. The GUI will open

### Direct Launch

```bash
python config_gui/main.py [optional_config_file]
```

## GUI Layout

- **Left Panel**: Image viewer with ROI overlays
  - Drag to select new ROIs
  - Existing ROIs shown as colored rectangles
- **Right Panel**: ROI management
  - List of all ROIs
  - Properties editor for selected ROI

## ROI Types

- **Rectangle ROIs**: Standard rectangular regions (x, y, width, height)
- **Engine ROIs**: Complex polygon shapes defined by points

## File Format

The GUI works with JSON config files containing:

```json
{
  "version": 6,
  "video_source": {"type": "twitter/x", "url": "..."},
  "time_unit": "frames",
  "vehicles": ["starship"],
  "rois": [
    {
      "id": "SH_SPEED",
      "vehicle": "superheavy",
      "label": "Superheavy Speed",
      "x": 359, "y": 913, "w": 83, "h": 25,
      "measurement_unit": "km/h"
    }
  ]
}
```

## Current Status

- ✅ Basic GUI framework
- ✅ ROI list and properties editor
- ✅ Config file loading/saving
- ✅ Interactive rectangle selection

## Dependencies

- PyQt6
- PIL/Pillow (for image loading)
