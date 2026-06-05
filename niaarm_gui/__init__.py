"""
NiaARM GUI - Graphical user interface for numerical association rule mining.

This package provides a PyQt6-based GUI for the NiaARM library.
"""

__version__ = "0.1.0"
__author__ = "Dario Zadravec"

# Export main window for easier imports
from niaarm_gui.main_window import NiaARMGUI

__all__ = ["NiaARMGUI"]