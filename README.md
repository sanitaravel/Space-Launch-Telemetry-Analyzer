# Space Launch Telemetry Analyzer

A small toolkit to analyze space launch flight recordings and extract telemetry and events from video.

This repository contains video-processing utilities, OCR-based telemetry extraction, plotting, and helper scripts used to analyze flight recordings (stored under `flight_recordings/`). It is intended for local analysis and lightweight automation (for example, publishing notable events).

## Key capabilities

- Extract text overlays and telemetry from videos using OCR (see `ocr/`).
- Process frames and regions-of-interest (ROIs) defined in `configs/`.
- Produce plots and analysis artifacts into `plot/` and `results/`.
- Download videos from multiple platforms (Twitter/X broadcasts and YouTube) and organize them by company and vehicle (see `download/`).

## Repository layout (important files/folders)

- `main.py` — primary entry point for running analyses.
- `download/` — video download utilities supporting multiple platforms (Twitter/X broadcasts and YouTube) with automatic organization by company and vehicle.
- `ocr/` — OCR helpers and models integration.
- `configs/` — ROI and configuration JSON files, organized by company and vehicle (e.g., `configs/spacex/starship/`, with `default_rois.json` at the root).
- `flight_recordings/` — sample and raw MP4 recordings used for analysis, organized by company and vehicle (e.g., `flight_recordings/spacex/starship/`, `flight_recordings/blue_origin/new_glenn/`).
- `plot/`, `results/` — output directories for plots and results, organized by company and vehicle (e.g., `results/spacex/starship/`, `results/blue_origin/new_glenn/`). Also includes comparison results across launches.
- `logs/` — runtime log files created when running the tools.
- `tests/` — unit and integration tests.
- `requirements.txt` — Python dependencies.

## Quick start

### Prerequisites

- Python 3.8+ is sufficient; Python 3.11/3.12 are recommended for best compatibility.
- FFmpeg installed and available on your `PATH` (used for frame extraction).
- (Optional) NVIDIA GPU with CUDA support — recommended if you plan to use GPU-accelerated OCR or ML models for significantly better performance.

### Install

Run the included installer (recommended). The repository provides a small installer script `setup.py` that wraps the `setup` package and automates virtual environment creation, dependency installation (including CUDA-aware PyTorch), and verification.

```pwsh
# Interactive installer (recommended)
python setup.py

# Example: unattended installation and force CPU-only PyTorch
python setup.py --unattended --force-cpu

# To update an existing installation
python setup.py --update
```

You can also run the installer directly as a module (equivalent):

```pwsh
python -c "import setup; setup.run_setup()"
```

If you prefer to manage the virtual environment and installation manually, follow these steps instead:

Create a virtual environment and install Python dependencies:

```pwsh
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Available installer flags (supported by `setup.py` / `setup.run_setup`):

- `--update` : Update dependencies in an existing virtual environment.
- `--force-cpu` : Force CPU-only installations (skip CUDA/PyTorch GPU variant).
- `--unattended` : Run without interactive prompts where possible.
- `--recreate` : Recreate the virtual environment if it already exists.
- `--keep` : Keep the existing virtual environment and skip recreation.
- `--debug` : Show detailed installation output for troubleshooting.

Note: On systems where the installer tries to install NVIDIA drivers or CUDA, you may need elevated privileges (sudo on Linux or administrator on Windows). The installer will guide you and print links for manual driver/CUDA downloads when automatic installation isn't appropriate.

### Run an analysis

The repository exposes `main.py`, which coordinates processing: parsing recordings (frame extraction, OCR-based telemetry parsing and event extraction) and generating plots/analysis artifacts saved to `plot/` and `results/`.

```pwsh
# Interactive menu (no args)
python main.py
```

`main.py` also supports lightweight profiling to help diagnose performance hotspots:

- `--profile` / `-p` : enable cProfile and write stats to `profile.stats` (or provide a filename).
- `--profile-print` : when profiling, print top functions by cumulative time after the run.
- `--profile-top N` : number of top functions to print (default 50).

See `python main.py --help` for the full set of options and menu-driven features.

## Configuration and ROIs

Region-of-interest (ROI) and flight-specific settings live in `configs/`. The file `configs/default_rois.json` provides a baseline. To analyze a recording with a specific ROI configuration, point the analysis to that JSON or copy/modify it for a flight.

### Available ROI Configurations

Pre-configured ROI files are available for specific flights:

- **SpaceX Starship**:
  - Flight 6: `configs/spacex/starship/flight_6_rois.json`
  - Flight 7: `configs/spacex/starship/flight_7_rois.json`
  - Flight 8: `configs/spacex/starship/flight_8_rois.json`
  - Flight 9: `configs/spacex/starship/flight_9_rois.json`
  - Flight 10: `configs/spacex/starship/flight_10_rois.json`
  - Flight 11: `configs/spacex/starship/flight_11_rois.json`

- **Blue Origin New Glenn**:
  - Flight 1: `configs/blue_origin/new_glenn/flight_1_rois.json`

Example ROI configuration (JSON) matching the project's schema:

```json
{
  "version": 5,
  "video_source": {
    "type": "twitter/x",
    "url": "https://x.com/i/broadcasts/1OwxWXMRAXmKQ"
  },
  "time_unit": "frames",
  "vehicles": ["superheavy", "starship"],
  "rois": [
    {
      "id": "speed",
      "vehicle": "superheavy",
      "label": "Superheavy Speed",
      "x": 1544,
      "y": 970,
      "w": 114,
      "h": 37,
      "start_time": 83301,
      "end_time": 88329,
      "measurement_unit": "km/h"
    },
    {
      "id": "altitude",
      "vehicle": "superheavy",
      "label": "Superheavy Altitude",
      "x": 1707,
      "y": 970,
      "w": 114,
      "h": 37,
      "start_time": 83301,
      "end_time": 88329,
      "measurement_unit": "km"
    },
    {
      "id": "time",
      "vehicle": null,
      "label": "Time Display",
      "x": 827,
      "y": 968,
      "w": 265,
      "h": 44,
      "start_time": 83301,
      "end_time": 168659,
      "measurement_unit": "[+-]\\d{2}:\\d{2}:\\d{2}"
    }
  ]
}
```

### ROI JSON field reference

Below are all fields observed in the `configs/` ROI files and their meanings. Use this as a quick reference when creating or editing ROI JSON files.

- `version` (integer)
  - Schema version for the ROI file. Increment when the format changes. Examples: `2`, `5`.

- `video_source` (object)
  - Information about the video source. Contains `type` (e.g., "twitter/x") and `url` fields.

- `time_unit` (string)
  - Unit used for `start_time` and `end_time`. Common values: `frames`, `seconds`.

- `vehicles` (array of strings)
  - List of vehicles present in the flight (e.g., `["superheavy", "starship"]`).

- `rois` (array of objects)
  - List of ROI objects; each object describes a single region to process.

Per-ROI object fields

- `id` (string)
  - Short unique identifier for the ROI (e.g., `speed`, `altitude`, `time`). Used to reference the ROI in logs and outputs.

- `vehicle` (string or null)
  - The vehicle this ROI applies to (e.g., `superheavy`, `starship`). Use `null` for ROIs that apply to the entire scene.

- `label` (string)
  - Human-friendly description of the ROI (e.g., `Superheavy Speed`). Used in UIs and reports.

- `x` (integer)
  - X coordinate (pixels) of the top-left corner of the ROI, relative to the frame's left edge.

- `y` (integer)
  - Y coordinate (pixels) of the top-left corner of the ROI, relative to the frame's top edge.

- `w` (integer)
  - Width (pixels) of the ROI rectangle.

- `h` (integer)
  - Height (pixels) of the ROI rectangle.

- `start_time` (integer or null)
  - When the ROI becomes active. Interpreted in the unit specified by `time_unit`. Use `null` if the ROI is active from the beginning.

- `end_time` (integer or null)
  - When the ROI stops being active. Interpreted in the unit specified by `time_unit`. Use `null` if the ROI remains active until the end of the recording.

- `measurement_unit` (string)
  - The unit of measurement for the data in this ROI (e.g., `km/h`, `km`, regex pattern for time like `[+-]\\d{2}:\\d{2}:\\d{2}`).

- `points` (object, optional)
  - For engine detection ROIs, defines key points for engine flame analysis. Contains arrays of [x,y] coordinates for different engine components.

- `match_to_role` (string, optional)
  - Legacy field for mapping to telemetry fields (e.g., `ss_altitude`). Used in older config versions.

Notes and best practices

- Coordinates and sizes are integer pixel values — double-check these values at the video resolution you are analyzing (e.g., 1920x1080 vs 1280x720).
- Use `start_time`/`end_time` to avoid running OCR on regions that are not present for the whole recording (this speeds up processing).
- Keep `id` values unique within a single file. You may reuse `id` values across ROIs if they apply to different vehicles or time ranges.
- When converting `seconds` to `frames`, multiply seconds by the video's frames-per-second (FPS). The project does not assume a default FPS — supply `time_unit` and values consistent with your workflow.
- `time_unit` indicates the unit used for `start_time`/`end_time` (e.g., `frames` or `seconds`).
- Coordinates are in pixels (`x`, `y`, `w`, `h`) relative to the top-left of the frame.
- `start_time` and `end_time` define when the ROI is active in the recording.
- `measurement_unit` specifies the expected format or unit of the extracted data (e.g., units like "km/h" or regex patterns for time).
- For engine detection, use the `points` field to define key coordinates for flame analysis.
- Save custom configs into the appropriate `configs/{company}/{vehicle}/` subdirectory and name them clearly (e.g., `configs/spacex/starship/flight_9_rois.json`).
- The analyzer will read the selected JSON and apply OCR or detection routines to each ROI; check logs in `logs/` for ROI processing messages.

## Contributing

Contributions are welcome. Please open issues for bugs or feature requests. For code changes, fork the repo, create a feature branch, and open a pull request against `master`.

## License

See the `LICENSE` file in the repository root for license details.

## Contact

If you need help running the project locally, open an issue or contact the repository owner.
