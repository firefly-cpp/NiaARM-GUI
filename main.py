"""
Main entry point for NiaARM GUI application.
"""

import sys
from PyQt6.QtWidgets import QApplication
from niaarm_gui.main_window import NiaARMGUI


def main():
    """Launch the NiaARM GUI application."""
    app = QApplication(sys.argv)
    window = NiaARMGUI()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()