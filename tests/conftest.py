import pytest
from niaarm_gui.main_window import NiaARMGUI


@pytest.fixture
def window(qtbot):
    """Creates the main window before each test and registers it for cleanup."""
    app_window = NiaARMGUI()
    qtbot.addWidget(app_window)
    return app_window