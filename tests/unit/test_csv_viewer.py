import os
import pytest
import shutil
import pandas as pd
from PyQt6.QtWidgets import QMessageBox
from niaarm_gui.csv_viewer import CsvEditorWindow

IRIS_CSV = os.path.join(os.path.dirname(__file__), "..", "test_data", "datasets", "iris.csv")


@pytest.fixture
def editor(qtbot, tmp_path):
    """Creates a CsvEditorWindow with a copy of Iris dataset for each test."""
    csv_copy = str(tmp_path / "iris_test.csv")
    shutil.copy(IRIS_CSV, csv_copy)
    window = CsvEditorWindow(csv_copy)
    # Override closeEvent to bypass unsaved changes dialog during test cleanup
    window.closeEvent = lambda event: event.accept()
    qtbot.addWidget(window)
    return window


# ── Initialization ─────────────────────────────────────────────────────────────

class TestInitialization:

    def test_window_title_contains_filename(self, editor):
        """Window title must contain the loaded CSV filename."""
        assert "iris_test.csv" in editor.windowTitle()

    def test_table_loaded_with_correct_row_count(self, editor):
        """Table must contain 150 rows after loading Iris dataset."""
        assert editor.table.rowCount() == 150

    def test_table_loaded_with_correct_column_count(self, editor):
        """Table must contain 5 columns (4 features + 1 class)."""
        assert editor.table.columnCount() == 5

    def test_no_unsaved_changes_on_start(self, editor):
        """has_unsaved_changes must be False on initialization."""
        assert not editor.has_unsaved_changes

    def test_original_data_stored(self, editor):
        """original_data must be populated after loading."""
        assert editor.original_data is not None
        assert editor.original_data.shape == (150, 5)


# ── Loading ────────────────────────────────────────────────────────────────────

class TestLoading:

    def test_header_labels_correct(self, editor):
        """Column headers must match the CSV column names."""
        df = pd.read_csv(IRIS_CSV)
        for col_idx, col_name in enumerate(df.columns):
            header = editor.table.horizontalHeaderItem(col_idx)
            assert header.text() == col_name


# ── Editing ────────────────────────────────────────────────────────────────────

class TestEditing:

    def test_add_row_increases_row_count(self, editor):
        """Adding a row must increase the row count by 1."""
        initial_count = editor.table.rowCount()
        editor._CsvEditorWindow__add_row()
        assert editor.table.rowCount() == initial_count + 1

    def test_add_row_marks_unsaved_changes(self, editor):
        """Adding a row must set has_unsaved_changes to True."""
        editor._CsvEditorWindow__add_row()
        assert editor.has_unsaved_changes


    def test_remove_row_decreases_row_count(self, editor):
        """Removing a row must decrease the row count by 1."""
        initial_count = editor.table.rowCount()
        editor._CsvEditorWindow__remove_row_at(0)
        assert editor.table.rowCount() == initial_count - 1

    def test_remove_row_marks_unsaved_changes(self, editor):
        """Removing a row must set has_unsaved_changes to True."""
        editor._CsvEditorWindow__remove_row_at(0)
        assert editor.has_unsaved_changes

    def test_add_column_increases_column_count(self, editor):
        """Adding a column must increase the column count by 1."""
        initial_count = editor.table.columnCount()
        editor._CsvEditorWindow__add_column()
        assert editor.table.columnCount() == initial_count + 1

    def test_remove_column_decreases_column_count(self, editor):
        """Removing a column must decrease the column count by 1."""
        initial_count = editor.table.columnCount()
        editor._CsvEditorWindow__remove_column_at(0)
        assert editor.table.columnCount() == initial_count - 1

    def test_remove_invalid_row_does_nothing(self, editor):
        """Removing a row at an invalid index must not change the row count."""
        initial_count = editor.table.rowCount()
        editor._CsvEditorWindow__remove_row_at(-1)
        editor._CsvEditorWindow__remove_row_at(9999)
        assert editor.table.rowCount() == initial_count

    def test_remove_invalid_column_does_nothing(self, editor):
        """Removing a column at an invalid index must not change the column count."""
        initial_count = editor.table.columnCount()
        editor._CsvEditorWindow__remove_column_at(-1)
        editor._CsvEditorWindow__remove_column_at(9999)
        assert editor.table.columnCount() == initial_count


# ── Reset ──────────────────────────────────────────────────────────────────────

class TestReset:

    def test_reset_restores_row_count(self, qtbot, editor, monkeypatch):
        """Resetting must restore the original row count after adding rows."""
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *args, **kwargs: QMessageBox.StandardButton.Yes
        )
        editor._CsvEditorWindow__add_row()
        editor._CsvEditorWindow__add_row()
        assert editor.table.rowCount() == 152

        editor._CsvEditorWindow__reset_table()
        assert editor.table.rowCount() == 150

    def test_reset_clears_unsaved_changes(self, qtbot, editor, monkeypatch):
        """Resetting must set has_unsaved_changes back to False."""
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *args, **kwargs: QMessageBox.StandardButton.Yes
        )
        editor._CsvEditorWindow__add_row()
        assert editor.has_unsaved_changes

        editor._CsvEditorWindow__reset_table()
        assert not editor.has_unsaved_changes


# ── Save ───────────────────────────────────────────────────────────────────────

class TestSave:

    def test_write_csv_creates_valid_file(self, editor, tmp_path, monkeypatch):
        """__write_csv() must create a valid CSV file with correct content."""
        monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
        output_path = str(tmp_path / "output.csv")
        editor._CsvEditorWindow__write_csv(output_path)

        df = pd.read_csv(output_path)
        assert df.shape == (150, 5)

    def test_write_csv_clears_unsaved_changes(self, editor, tmp_path, monkeypatch):
        """__write_csv() must set has_unsaved_changes to False after saving."""
        monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
        editor._CsvEditorWindow__add_row()
        assert editor.has_unsaved_changes

        output_path = str(tmp_path / "output.csv")
        editor._CsvEditorWindow__write_csv(output_path)
        assert not editor.has_unsaved_changes

    def test_write_csv_preserves_headers(self, editor, tmp_path, monkeypatch):
        """Saved CSV must have the same column headers as the original."""
        monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
        output_path = str(tmp_path / "output.csv")
        editor._CsvEditorWindow__write_csv(output_path)

        original_df = pd.read_csv(IRIS_CSV)
        saved_df = pd.read_csv(output_path)
        assert list(original_df.columns) == list(saved_df.columns)