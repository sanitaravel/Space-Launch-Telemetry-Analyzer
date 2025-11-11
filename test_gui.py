#!/usr/bin/env python3
"""
Simple test script for the ROI GUI.
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config_gui.main import ROIConfigurator
    print("GUI import successful!")
    print("You can now run the GUI with: python config_gui/main.py")
except ImportError as e:
    print(f"Import failed: {e}")
    print("Make sure PyQt6 is installed:")
    print("pip install PyQt6")