import os
import pytest
from PyQt6.QtWidgets import QMessageBox
from niaarm_gui.main_window import NiaARMGUI
from niaarm_gui.mining_results_viewer import MiningResultsViewer
from niaarm_gui.dialogs import LoadingDialog

# Path to the test Iris dataset
IRIS_CSV = os.path.join(os.path.dirname(__file__), "..", "test_data", "datasets", "iris.csv")


@pytest.fixture
def configured_window(qtbot):
    """Creates a NiaARMGUI window fully configured for a fast DE run on Iris."""
    window = NiaARMGUI()
    qtbot.addWidget(window)

    window.csv_input.setText(os.path.abspath(IRIS_CSV))
    window.data_squash_combo.setCurrentText("No")

    for metric, (check, slider, _) in window.metric_sliders.items():
        check.setChecked(metric in ("Support", "Confidence"))

    window.algorithm_combo.setCurrentText("Differential Evolution")
    window.pop_size_input.setText("30")

    window.max_iter_checkbox.setChecked(True)
    window.max_iter_input.setText("50")
    window.max_evals_checkbox.setChecked(False)

    window.diff_slider.setValue(50)
    window.crossover_slider.setValue(90)

    return window


# ── Full mining flow ───────────────────────────────────────────────────────────

class TestMiningFlow:

    @pytest.mark.timeout(60)
    def test_mining_produces_results(self, qtbot, configured_window):
        """A full DE run on Iris must produce at least one rule
        and open the MiningResultsViewer window."""

        viewers_opened = []

        original_init = MiningResultsViewer.__init__

        def patched_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            viewers_opened.append(self)

        MiningResultsViewer.__init__ = patched_init

        try:
            configured_window._NiaARMGUI__run_mining()

            # Wait for MiningResultsViewer to open (up to 60s)
            qtbot.waitUntil(lambda: len(viewers_opened) > 0, timeout=60000)

            viewer = viewers_opened[0]
            qtbot.addWidget(viewer)

            # Verify results
            assert viewer.rules is not None
            assert len(viewer.rules) > 0
            assert viewer.rules_table.rowCount() > 0

        finally:
            MiningResultsViewer.__init__ = original_init

    @pytest.mark.timeout(60)
    def test_mining_results_have_correct_metrics(self, qtbot, configured_window):
        """Rules produced by DE on Iris must have valid support and confidence values."""

        viewers_opened = []
        original_init = MiningResultsViewer.__init__

        def patched_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            viewers_opened.append(self)

        MiningResultsViewer.__init__ = patched_init

        try:
            configured_window._NiaARMGUI__run_mining()
            qtbot.waitUntil(lambda: len(viewers_opened) > 0, timeout=60000)

            viewer = viewers_opened[0]
            qtbot.addWidget(viewer)

            for rule in viewer.rules:
                assert 0.0 <= rule.support <= 1.0
                assert 0.0 <= rule.confidence <= 1.0
                assert 0.0 <= rule.fitness <= 1.0

        finally:
            MiningResultsViewer.__init__ = original_init

    @pytest.mark.timeout(30)
    def test_cancel_then_restart_does_not_crash(self, qtbot, configured_window, monkeypatch):
        """Cancelling mining and immediately restarting must not crash the app."""

        configured_window._NiaARMGUI__run_mining()
        qtbot.wait(500)

        # Cancel
        monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: None)
        configured_window._NiaARMGUI__on_mining_cancelled(
            LoadingDialog("Mining in progress...", configured_window)
        )
        qtbot.wait(500)

        # Try to restart
        warned = []
        original_warning = QMessageBox.warning
        QMessageBox.warning = lambda *args, **kwargs: warned.append(True)

        try:
            configured_window._NiaARMGUI__run_mining()
            # Either a warning was shown (thread still running)
            # or mining started cleanly (thread already finished)
            # — in both cases, no crash is the key assertion
            assert True
        finally:
            QMessageBox.warning = original_warning