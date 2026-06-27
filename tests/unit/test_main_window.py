import pytest
import os
from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog
from PyQt6.QtCore import Qt
from niaarm_gui.main_window import NiaARMGUI

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "test_data")
DATASETS_DIR = os.path.join(TEST_DATA_DIR, "datasets")
PIPELINES_DIR = os.path.join(TEST_DATA_DIR, "pipelines")

# ── Initialization ────────────────────────────────────────────────────────────

class TestInitialization:

    def test_window_title(self, window):
        """The window must have the correct title."""
        assert window.windowTitle() == "NiaARM GUI"

    def test_csv_input_empty_on_start(self, window):
        """The CSV input field must be empty on startup."""
        assert window.csv_input.text() == ""

    def test_default_population_size(self, window):
        """The default population size must be 50."""
        assert window.pop_size_input.text() == "50"

    def test_default_max_iterations(self, window):
        """The default number of iterations must be 100."""
        assert window.max_iter_input.text() == "100"

    def test_default_algorithm_selection(self, window):
        """The default algorithm selection must be 'Select Algorithm'."""
        assert window.algorithm_combo.currentText() == "Select Algorithm"

    def test_data_squashing_disabled_by_default(self, window):
        """Data squashing must be disabled by default."""
        assert window.data_squash_combo.currentText() == "No"


# ── CSV configuration ────────────────────────────────────────────────────────────

class TestCsvConfiguration:

    def test_empty_file_shows_warning(self, qtbot, window, monkeypatch, tmp_path):
        """Selecting an empty CSV file must show a warning."""
        warned = []
        monkeypatch.setattr(QMessageBox, "warning",
                            lambda *args, **kwargs: warned.append(True))
        monkeypatch.setattr(QFileDialog, "getOpenFileName",
                            lambda *args, **kwargs: (os.path.join(DATASETS_DIR, "empty.csv"), ""))
        window._NiaARMGUI__select_csv()
        assert len(warned) == 1

    def test_non_comma_delimiter_shows_conversion_dialog(self, qtbot, window, monkeypatch):
        """Selecting a CSV with semicolon delimiter must ask user about conversion."""
        questioned = []
        monkeypatch.setattr(QMessageBox, "question",
                            lambda *args, **kwargs: questioned.append(True) or QMessageBox.StandardButton.No)
        monkeypatch.setattr(QFileDialog, "getOpenFileName",
                            lambda *args, **kwargs: (os.path.join(DATASETS_DIR, "semicolon.csv"), ""))
        window._NiaARMGUI__select_csv()
        assert len(questioned) == 1

    def test_comma_delimiter_sets_csv_path(self, qtbot, window, monkeypatch):
        """Selecting a valid comma-delimited CSV must set the csv_input path."""
        monkeypatch.setattr(QFileDialog, "getOpenFileName",
                            lambda *args, **kwargs: (os.path.join(DATASETS_DIR, "iris.csv"), ""))
        window._NiaARMGUI__select_csv()
        assert window.csv_input.text() == os.path.join(DATASETS_DIR, "iris.csv")

    def test_view_csv_without_selection_shows_error(self, qtbot, window, monkeypatch):
        """Clicking Edit file without first selecting a CSV must show a warning."""
        warned = []
        monkeypatch.setattr(QMessageBox, "warning",
                            lambda *args, **kwargs: warned.append(True))
        window._NiaARMGUI__view_csv()
        assert len(warned) == 1


# ── Data squashing ────────────────────────────────────────────────────────────

class TestDataSquashing:

    def test_squashing_settings_hidden_by_default(self, window):
        """Data squashing settings must be hidden when 'No' is selected."""
        assert window.threshold_label.isHidden()
        assert window.ds_threshold_slider.isHidden()
        assert window.similarity_label.isHidden()

    def test_squashing_settings_visible_when_enabled(self, qtbot, window):
        """Data squashing settings must appear when 'Yes' is selected."""
        window.data_squash_combo.setCurrentText("Yes")
        assert not window.threshold_label.isHidden()
        assert not window.ds_threshold_slider.isHidden()
        assert not window.similarity_label.isHidden()

    def test_default_threshold_value(self, window):
        """The default threshold value must be 0.50."""
        assert window.ds_threshold_value_label.text() == "0.50"

    def test_similarity_options(self, window):
        """The similarity combo box must contain exactly two options."""
        options = [window.similarity_combo.itemText(i)
                   for i in range(window.similarity_combo.count())]
        assert "Euclidean" in options
        assert "Cosine" in options
        assert len(options) == 2


# ── Algorithm selection ────────────────────────────────────────────────────────

class TestAlgorithmSelection:

    def test_algorithm_combo_has_five_algorithms(self, window):
        """The combo box must contain 5 algorithms and 'Select Algorithm' options."""
        assert window.algorithm_combo.count() == 6

    def test_de_sliders_visible_when_selected(self, qtbot, window):
        """Selecting DE must show its sliders."""
        window.algorithm_combo.setCurrentText("Differential Evolution")
        assert not window.diff_slider.isHidden()
        assert not window.crossover_slider.isHidden()

    def test_pso_sliders_visible_when_selected(self, qtbot, window):
        """Selecting PSO must show its sliders."""
        window.algorithm_combo.setCurrentText("Particle Swarm Optimization")
        assert not window.c1_slider.isHidden()
        assert not window.c2_slider.isHidden()
        assert not window.w_slider.isHidden()

    def test_algorithm_switch_hides_previous_sliders(self, qtbot, window):
        """Switching algorithms must hide the previous algorithm's sliders."""
        window.algorithm_combo.setCurrentText("Differential Evolution")
        window.algorithm_combo.setCurrentText("Genetic Algorithm")
        assert window.diff_slider.isHidden()
        assert not window.ga_crossover_slider.isHidden()

    def test_bat_fmin_fmax_constraint(self, qtbot, window):
        """fmin must never be allowed to exceed fmax, and vice versa."""
        window.algorithm_combo.setCurrentText("Bat Algorithm")
        window.fmax_slider.setValue(50)   # 0.50
        window.fmin_slider.setValue(100)  # 1.00 -> should be clamped to 50
        assert window.fmin_slider.value() <= window.fmax_slider.value()


# ── Buttons and dialogs ────────────────────────────────────────────────────────

class TestButtons:

    def test_dataset_info_without_csv_shows_error(self, qtbot, window, monkeypatch):
        """Clicking Dataset Info without a loaded file must show a warning."""
        warned = []
        monkeypatch.setattr(
            QMessageBox, "warning",
            lambda *args, **kwargs: warned.append(True)
        )
        window.csv_info_button.click()
        assert len(warned) == 1


# ── Pipeline import/export ──────────────────────────────────────────────────────

class TestPipeline:

    def test_export_import_roundtrip(self, qtbot, window):
        """A pipeline exported to JSON must restore the same configuration on import."""
        window.algorithm_combo.setCurrentText("Genetic Algorithm")
        window.pop_size_input.setText("30")
        window.max_iter_input.setText("60")
        window.ga_crossover_slider.setValue(70)
        window.ga_mutation_slider.setValue(10)

        pipeline_path = os.path.join(PIPELINES_DIR, "ga_test_pipeline.json")
        window._NiaARMGUI__export_pipeline_to_path(pipeline_path)

        window.algorithm_combo.setCurrentText("Select Algorithm")
        window.pop_size_input.setText("50")
        window.max_iter_input.setText("100")

        window._NiaARMGUI__import_pipeline_from_path(pipeline_path)

        assert window.algorithm_combo.currentText() == "Genetic Algorithm"
        assert window.pop_size_input.text() == "30"
        assert window.max_iter_input.text() == "60"
        assert window.ga_crossover_slider.value() == 70
        assert window.ga_mutation_slider.value() == 10

    def test_import_missing_dataset_shows_warning(self, qtbot, window, monkeypatch):
        """Importing a pipeline with a non-existent dataset path must warn the user."""
        warned = []
        monkeypatch.setattr(
            QMessageBox, "warning",
            lambda *args, **kwargs: warned.append(True)
        )
        pipeline_path = os.path.join(PIPELINES_DIR, "missing_dataset.json")
        window._NiaARMGUI__import_pipeline_from_path(pipeline_path)
        assert len(warned) == 1