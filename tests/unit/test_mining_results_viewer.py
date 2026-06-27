import pytest
import os
import csv
import openpyxl
from PyQt6.QtWidgets import QMessageBox
from niaarm_gui.mining_results_viewer import MiningResultsViewer


MINING_RESULTS_CSV = os.path.join(os.path.dirname(__file__), "..", "test_data", "datasets", "iris_pso.csv")


@pytest.fixture
def viewer(qtbot):
    """Creates a MiningResultsViewer loaded from real mining results CSV."""
    v = MiningResultsViewer(file_path=MINING_RESULTS_CSV)
    qtbot.addWidget(v)
    return v


@pytest.fixture
def empty_viewer(qtbot):
    """Creates a MiningResultsViewer with no rules."""
    v = MiningResultsViewer(rules=[], time=0.0)
    qtbot.addWidget(v)
    return v


# ── Initialization ─────────────────────────────────────────────────────────────

class TestInitialization:

    def test_window_title(self, viewer):
        """Window must have correct title."""
        assert "Mining Results" in viewer.windowTitle()

    def test_table_loaded_with_rules(self, viewer):
        """Table must contain at least one rule after loading from CSV."""
        assert viewer.rules_table.rowCount() > 0

    def test_rules_count_matches_table_rows(self, viewer):
        """Number of rules must match the number of table rows."""
        assert viewer.rules_table.rowCount() == len(viewer.rules)

    def test_table_column_count(self, viewer):
        """Table must have 16 columns."""
        assert viewer.rules_table.columnCount() == 16

    def test_empty_viewer_has_no_rows(self, empty_viewer):
        """Table must be empty when no rules are provided."""
        assert empty_viewer.rules_table.rowCount() == 0


# ── Filtering ──────────────────────────────────────────────────────────────────

class TestFiltering:

    def test_filter_by_support_reduces_rows(self, viewer):
        """Filtering by a support threshold must reduce the number of visible rows."""
        all_rules = viewer.rules
        threshold = 0.5
        expected = sum(1 for r in all_rules if r.support >= threshold)

        viewer.active_filters = {"support": threshold}
        viewer.filtered_rules = [r for r in all_rules if r.support >= threshold]
        viewer._MiningResultsViewer__update_table()

        assert viewer.rules_table.rowCount() == expected
        assert viewer.rules_table.rowCount() < len(all_rules)

    def test_filter_by_confidence_reduces_rows(self, viewer):
        """Filtering by a confidence threshold must reduce the number of visible rows."""
        all_rules = viewer.rules
        threshold = 0.7
        expected = sum(1 for r in all_rules if r.confidence >= threshold)

        viewer.active_filters = {"confidence": threshold}
        viewer.filtered_rules = [r for r in all_rules if r.confidence >= threshold]
        viewer._MiningResultsViewer__update_table()

        assert viewer.rules_table.rowCount() == expected

    def test_filter_with_no_matching_rules(self, viewer):
        """Filtering with threshold 1.0 must result in an empty table."""
        viewer.active_filters = {"support": 1.0}
        viewer.filtered_rules = []
        viewer._MiningResultsViewer__update_table()
        assert viewer.rules_table.rowCount() == 0

    def test_clear_filter_restores_all_rules(self, viewer):
        """Clearing filters must restore all rules in the table."""
        all_count = len(viewer.rules)

        viewer.active_filters = {"support": 1.0}
        viewer.filtered_rules = []
        viewer._MiningResultsViewer__update_table()
        assert viewer.rules_table.rowCount() == 0

        viewer.active_filters = {}
        viewer.filtered_rules = list(viewer.rules)
        viewer._MiningResultsViewer__update_table()
        assert viewer.rules_table.rowCount() == all_count


# ── CSV export ─────────────────────────────────────────────────────────────────

class TestCsvExport:

    def test_save_to_csv_creates_file(self, viewer, tmp_path, monkeypatch):
        """__save_to_csv() must create a valid CSV file at the specified path."""
        monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
        csv_path = str(tmp_path / "test_rules.csv")
        viewer._MiningResultsViewer__save_to_csv(csv_path)
        assert (tmp_path / "test_rules.csv").exists()

    def test_save_to_csv_correct_row_count(self, viewer, tmp_path, monkeypatch):
        """Exported CSV must contain a header row plus one row per rule."""
        monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
        csv_path = str(tmp_path / "test_rules.csv")
        viewer._MiningResultsViewer__save_to_csv(csv_path)
        with open(csv_path, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 630

    def test_save_to_csv_header_row(self, viewer, tmp_path, monkeypatch):
        """Exported CSV must contain the correct header columns."""
        monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
        csv_path = str(tmp_path / "test_rules.csv")
        viewer._MiningResultsViewer__save_to_csv(csv_path)
        with open(csv_path, "r") as f:
            reader = csv.reader(f)
            headers = next(reader)
        assert "antecedent" in headers
        assert "consequent" in headers
        assert "fitness" in headers

# ── Excel export ───────────────────────────────────────────────────────────────

class TestExcelExport:

    def test_export_to_excel_creates_file(self, viewer, tmp_path, monkeypatch):
        """__export_to_excel() must create a valid Excel file at the specified path."""
        monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

        excel_path = str(tmp_path / "test_rules.xlsx")
        monkeypatch.setattr(
            "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
            lambda *args, **kwargs: (excel_path, "Excel Files (*.xlsx)")
        )
        viewer._MiningResultsViewer__export_to_excel()
        assert (tmp_path / "test_rules.xlsx").exists()

    def test_export_to_excel_correct_row_count(self, viewer, tmp_path, monkeypatch):
        """Exported Excel file must contain a header row plus one row per rule."""
        monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

        excel_path = str(tmp_path / "test_rules.xlsx")
        monkeypatch.setattr(
            "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
            lambda *args, **kwargs: (excel_path, "Excel Files (*.xlsx)")
        )
        viewer._MiningResultsViewer__export_to_excel()
        wb = openpyxl.load_workbook(excel_path)
        ws = wb.active
        assert ws.max_row == 630