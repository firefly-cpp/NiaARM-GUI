import pytest
import os
import csv
import pandas as pd
from PyQt6.QtWidgets import QMessageBox, QLabel
from niaarm_gui.dialogs import LoadingDialog, ProgressDialog, FilterDialog, DatasetInfoDialog

IRIS_CSV = os.path.join(os.path.dirname(__file__), "..", "test_data", "datasets", "iris.csv")


# ── LoadingDialog ─────────────────────────────────────────────────────────────

class TestLoadingDialog:
    @pytest.fixture
    def dialog(self, qtbot):
        """Creates a LoadingDialog before each test and registers it for cleanup."""
        d = LoadingDialog("Mining in progress...")
        qtbot.addWidget(d)
        return d

    def test_default_text(self, dialog):
        """The dialog must display the text passed in the constructor."""
        assert dialog.label.text() == "Mining in progress..."

    def test_set_text_updates_label(self, dialog):
        """set_text() must update the main label."""
        dialog.set_text("Data squashing in progress...")
        assert dialog.label.text() == "Data squashing in progress..."

    def test_squash_info_hidden_by_default(self, dialog):
        """The squash info label must be hidden before set_squash_info() is called."""
        assert dialog.squash_info_label.isHidden()

    def test_set_squash_info_shows_label(self, dialog):
        """set_squash_info() must make the squash info label visible."""
        dialog.set_squash_info(4177, 487)
        assert not dialog.squash_info_label.isHidden()

    def test_set_squash_info_correct_reduction(self, dialog):
        """set_squash_info() must calculate the correct reduction percentage."""
        dialog.set_squash_info(4177, 487)
        text = dialog.squash_info_label.text()
        assert "4177" in text
        assert "487" in text
        assert "88.3%" in text

    def test_set_squash_info_full_squash(self, dialog):
        """set_squash_info() must handle edge case of 100% reduction correctly."""
        dialog.set_squash_info(1000, 0)
        text = dialog.squash_info_label.text()
        assert "100.0%" in text

    def test_is_cancelled_false_by_default(self, dialog):
        """is_cancelled() must return False before any cancellation."""
        assert not dialog.is_cancelled()

    def test_show_completed_updates_label(self, dialog):
        """show_completed() must update the label to show completion message."""
        dialog.show_completed()
        assert "completed" in dialog.label.text().lower()

    def test_show_completed_hides_cancel_button(self, dialog):
        """show_completed() must hide the cancel button."""
        dialog.show_completed()
        assert dialog.cancel_button.isHidden()

    def test_progress_info_label_empty_by_default(self, dialog):
        """The progress info label must be empty on initialization."""
        assert dialog.progress_info_label.text() == ""

    def test_progress_info_label_update(self, dialog):
        """The progress info label must correctly display iteration info."""
        dialog.progress_info_label.setText("Iteration 5 / 100")
        assert dialog.progress_info_label.text() == "Iteration 5 / 100"


# ── ProgressDialog ────────────────────────────────────────────────────────────

class TestProgressDialog:
    @pytest.fixture
    def dialog(self, qtbot):
        """Creates a ProgressDialog before each test and registers it for cleanup."""
        d = ProgressDialog("Loading rules...", 1000)
        qtbot.addWidget(d)
        return d

    def test_max_value(self, dialog):
        """ProgressDialog must be initialized with the correct maximum value."""
        assert dialog.maximum() == 1000

    def test_initial_value(self, dialog):
        """ProgressDialog must have value at -1 before start."""
        assert dialog.value() == -1

    def test_set_value_updates_progress(self, dialog):
        """setValue() must update the progress bar value."""
        dialog.setValue(500)
        assert dialog.value() == 500

    def test_not_cancelled_by_default(self, dialog):
        """ProgressDialog must not be cancelled on initialization."""
        assert not dialog.wasCanceled()

    def test_window_title(self, dialog):
        """ProgressDialog must have correct window title."""
        assert dialog.windowTitle() == "Loading"


# ── DatasetInfoDialog ──────────────────────────────────────────────────────────

class TestDatasetInfoDialog:

    @pytest.fixture
    def dialog(self, qtbot):
        """Creates a DatasetInfoDialog loaded from the Iris dataset."""
        d = DatasetInfoDialog(IRIS_CSV)
        qtbot.addWidget(d)
        return d

    def test_window_title_contains_filename(self, dialog):
        """Window title must contain the CSV filename."""
        assert "iris.csv" in dialog.windowTitle()

    def test_dialog_opens_without_error(self, qtbot):
        """DatasetInfoDialog must open without raising an exception."""
        try:
            d = DatasetInfoDialog(IRIS_CSV)
            qtbot.addWidget(d)
        except Exception as e:
            pytest.fail(f"DatasetInfoDialog raised an exception: {e}")

    def test_overview_shows_correct_row_count(self, dialog):
        """Overview card must show 150 rows for Iris dataset."""
        labels = dialog.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        assert "150" in texts

    def test_overview_shows_correct_column_count(self, dialog):
        """Overview card must show 5 total attributes for Iris dataset."""
        labels = dialog.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        assert "5" in texts

    def test_numerical_min_max_values_correct(self, dialog):
        """Numerical attribute stats must match pandas-computed min/max values."""
        df = pd.read_csv(IRIS_CSV)
        numerical_cols = df.select_dtypes(include=["number"]).columns.tolist()
        labels = dialog.findChildren(QLabel)
        all_text = " ".join(lbl.text() for lbl in labels)

        for col in numerical_cols:
            expected_min = str(round(df[col].min(), 4))
            expected_max = str(round(df[col].max(), 4))
            assert expected_min in all_text, f"min value for {col} not found in dialog"
            assert expected_max in all_text, f"max value for {col} not found in dialog"

    def test_categorical_values_shown(self, dialog):
        """Categorical attribute card must show all Iris species."""
        labels = dialog.findChildren(QLabel)
        all_text = " ".join(lbl.text() for lbl in labels)
        assert "setosa" in all_text
        assert "versicolor" in all_text
        assert "virginica" in all_text

    def test_categories_truncated_at_ten(self, qtbot, tmp_path):
        """Categorical column with more than 10 unique values must be truncated with ..."""
        csv_path = str(tmp_path / "many_categories.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["value", "category"])
            for i in range(15):
                writer.writerow([i, f"cat_{i}"])

        d = DatasetInfoDialog(csv_path)
        qtbot.addWidget(d)
        labels = d.findChildren(QLabel)
        all_text = " ".join(lbl.text() for lbl in labels)
        assert "..." in all_text


# ── FilterDialog ───────────────────────────────────────────────────────────────

class TestFilterDialog:

    @pytest.fixture
    def dialog(self, qtbot):
        """Creates a FilterDialog for each test."""
        d = FilterDialog()
        qtbot.addWidget(d)
        return d

    def test_all_checkboxes_unchecked_by_default(self, dialog):
        """All filter checkboxes must be unchecked on initialization."""
        for checkbox, _ in dialog.metric_inputs.values():
            assert not checkbox.isChecked()

    def test_all_inputs_disabled_by_default(self, dialog):
        """All input fields must be disabled when checkboxes are unchecked."""
        for _, input_field in dialog.metric_inputs.values():
            assert not input_field.isEnabled()

    def test_checking_checkbox_enables_input(self, dialog):
        """Checking a metric checkbox must enable its input field."""
        checkbox, input_field = dialog.metric_inputs["support"]
        checkbox.setChecked(True)
        assert input_field.isEnabled()

    def test_get_filters_empty_when_nothing_checked(self, dialog):
        """get_filters() must return an empty dict when no metrics are selected."""
        assert dialog.get_filters() == {}

    def test_get_filters_returns_correct_value(self, dialog):
        """get_filters() must return the correct threshold for a checked metric."""
        checkbox, input_field = dialog.metric_inputs["support"]
        checkbox.setChecked(True)
        input_field.setText("0.75")
        filters = dialog.get_filters()
        assert "support" in filters
        assert filters["support"] == 0.75

    def test_get_filters_multiple_metrics(self, dialog):
        """get_filters() must return all checked metrics with their values."""
        for attr in ["support", "confidence", "fitness"]:
            checkbox, input_field = dialog.metric_inputs[attr]
            checkbox.setChecked(True)
            input_field.setText("0.5")

        filters = dialog.get_filters()
        assert len(filters) == 3
        assert all(v == 0.5 for v in filters.values())

    def test_reset_filters_unchecks_all(self, dialog):
        """reset_filters() must uncheck all checkboxes."""
        for checkbox, _ in dialog.metric_inputs.values():
            checkbox.setChecked(True)

        dialog.reset_filters()

        for checkbox, _ in dialog.metric_inputs.values():
            assert not checkbox.isChecked()

    def test_reset_filters_resets_values(self, dialog):
        """reset_filters() must reset all input values to 0.0."""
        for checkbox, input_field in dialog.metric_inputs.values():
            checkbox.setChecked(True)
            input_field.setText("0.9")

        dialog.reset_filters()

        for _, input_field in dialog.metric_inputs.values():
            assert input_field.text() == "0.0"

    def test_all_twelve_metrics_present(self, dialog):
        """FilterDialog must contain all 12 metric inputs."""
        assert len(dialog.metric_inputs) == 12