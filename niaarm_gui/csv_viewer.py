import os
import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QFileDialog, QTableWidget, QTableWidgetItem, QMessageBox, \
    QMenu
from PyQt6.QtGui import QAction


class CsvEditorWindow(QMainWindow):
    def __init__(self, csv_path):
        super().__init__()
        self.setWindowTitle("CSV Editor")
        self.setGeometry(100, 100, 800, 600)

        self.csv_path = csv_path
        self.original_data = None
        self.has_unsaved_changes = False

        self.__create_menu_bar()
        self.__create_status_bar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        self.table = QTableWidget()
        self.table.setStyleSheet("background-color: white; color: black;")
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.__show_context_menu)
        self.table.itemChanged.connect(self.__on_table_changed)

        layout.addWidget(self.table)

        self.__load_csv(self.csv_path)

    def __create_menu_bar(self):
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #34495e;
                color: white;
            }
            QMenuBar::item:selected {
                background-color: #2c3e50;
            }
            QMenu {
                background-color: white;
                color: black;
            }
            QMenu::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)

        # File menu
        file_menu = menu_bar.addMenu("File")

        # Save action
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.__save_csv)
        file_menu.addAction(save_action)

        # Save As action
        save_as_action = QAction("Save As...", self)
        save_as_action.triggered.connect(self.__save_csv_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menu_bar.addMenu("Edit")

        add_row_action = QAction("Add Row", self)
        add_row_action.triggered.connect(self.__add_row)
        edit_menu.addAction(add_row_action)

        add_col_action = QAction("Add Column", self)
        add_col_action.triggered.connect(self.__add_column)
        edit_menu.addAction(add_col_action)

        edit_menu.addSeparator()

        reset_action = QAction("Reset Table", self)
        reset_action.setShortcut("Ctrl+R")
        reset_action.triggered.connect(self.__reset_table)
        edit_menu.addAction(reset_action)

    def __create_status_bar(self):
        status_bar = self.statusBar()
        status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #34495e;
                color: white;
                font-size: 11px;
                padding: 3px;
                border-top: 1px solid #2c3e50;
            }
        """)
        status_bar.showMessage("NiaARM GUI v1.0")

    def __show_context_menu(self, position):
        """Shows context menu (right click)"""
        item = self.table.itemAt(position)
        if item is None:
            return

        row = item.row()
        col = item.column()

        context_menu = QMenu(self)
        context_menu.setStyleSheet("""
            QMenu {
                background-color: white;
                color: black;
                border: 1px solid #bdc3c7;
            }
            QMenu::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)

        remove_row_action = QAction(f"Remove Row", self)
        remove_row_action.triggered.connect(lambda: self.__remove_row_at(row))
        context_menu.addAction(remove_row_action)

        remove_col_action = QAction(f"Remove Column", self)
        remove_col_action.triggered.connect(lambda: self.__remove_column_at(col))
        context_menu.addAction(remove_col_action)

        context_menu.exec(self.table.viewport().mapToGlobal(position))

    def __load_csv(self, file_path):
        """Loads CSV data in self.table"""
        if not os.path.exists(file_path):
            QMessageBox.critical(self, "Error", f"File not found:\n{file_path}")
            return

        try:
            df = pd.read_csv(file_path)

            if df.empty:
                QMessageBox.warning(self, "Warning", "CSV file is empty!")
                return

            self.original_data = df.copy()

            self.__fill_table(df)

            self.csv_path = file_path
            self.setWindowTitle(f"CSV Editor - {os.path.basename(file_path)}")
            self.statusBar().showMessage(
                f"Loaded: {file_path} ({df.shape[0]} rows, {df.shape[1]} columns)",
                5000
            )

        except pd.errors.EmptyDataError:
            QMessageBox.critical(self, "Error", "CSV file is empty!")
        except pd.errors.ParserError as e:
            QMessageBox.critical(self, "Error", f"Failed to parse CSV file:\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load CSV file:\n{str(e)}")

    def __fill_table(self, df):
        """Fills the table with given dataset"""
        self.table.itemChanged.disconnect(self.__on_table_changed)

        self.table.setRowCount(df.shape[0])
        self.table.setColumnCount(df.shape[1])

        self.table.setHorizontalHeaderLabels(df.columns.tolist())

        for row_idx in range(len(df)):
            for col_idx in range(len(df.columns)):
                value = df.iloc[row_idx, col_idx]
                display_value = "" if pd.isna(value) else str(value)
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(display_value))

        self.table.itemChanged.connect(self.__on_table_changed)

    def __reset_table(self):
        """Resets the table"""
        if self.original_data is None:
            QMessageBox.warning(self, "Warning", "No original data to restore!")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Reset",
            "Are you sure you want to reset the table to its original state?\n\n"
            "All unsaved changes will be lost!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.has_unsaved_changes = False
            self.__fill_table(self.original_data)
            self.statusBar().showMessage("Table reset to original state", 3000)

    def __save_csv(self):
        """Saves dataset into existing file (current location)"""
        if self.csv_path:
            self.__write_csv(self.csv_path)
        else:
            self.__save_csv_as()

    def __save_csv_as(self):
        """Saves dataset in a new CSV file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save CSV File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            if not file_path.endswith('.csv'):
                file_path += '.csv'

            self.__write_csv(file_path)
            self.csv_path = file_path
            self.setWindowTitle(f"CSV Editor - {os.path.basename(file_path)}")

    def __write_csv(self, file_path):
        """Writes dataset from self.table into CSV"""
        try:
            data = []
            headers = []

            for col in range(self.table.columnCount()):
                header_item = self.table.horizontalHeaderItem(col)
                headers.append(header_item.text() if header_item else f"Column_{col}")

            for row in range(self.table.rowCount()):
                row_data = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else "")
                data.append(row_data)

            df = pd.DataFrame(data, columns=headers)
            df.to_csv(file_path, index=False, encoding='utf-8')

            self.has_unsaved_changes = False
            self.statusBar().showMessage(f"Saved: {file_path}", 5000)
            QMessageBox.information(self, "Success", f"File saved successfully:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file:\n{str(e)}")

    def __add_row(self):
        """Adds new empty row in self.table"""
        current_row_count = self.table.rowCount()
        self.table.insertRow(current_row_count)
        self.has_unsaved_changes = True
        self.statusBar().showMessage(f"Row {current_row_count + 1} added", 3000)

    def __remove_row_at(self, row):
        """Removes selected row from the table"""
        if row < 0 or row >= self.table.rowCount():
            return

        self.table.removeRow(row)
        self.has_unsaved_changes = True
        self.statusBar().showMessage(f"Row {row + 1} removed", 3000)

    def __add_column(self):
        """Adds new empty column in self.table"""
        current_col_count = self.table.columnCount()
        self.table.insertColumn(current_col_count)
        self.has_unsaved_changes = True
        self.statusBar().showMessage(f"Column {current_col_count + 1} added", 3000)

    def __remove_column_at(self, col):
        """Removes selected column from the table"""
        if col < 0 or col >= self.table.columnCount():
            return

        self.table.removeColumn(col)
        self.has_unsaved_changes = True
        self.statusBar().showMessage(f"Column {col + 1} removed", 3000)

    def __on_table_changed(self, item):
        """Calls when user changes table content"""
        self.has_unsaved_changes = True

    def closeEvent(self, event):
        """Overrides the event when user closes window"""
        if self.has_unsaved_changes:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes.\n\n"
                "Do you want to save before closing?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )

            if reply == QMessageBox.StandardButton.Save:
                self.__save_csv()

                if not self.has_unsaved_changes:
                    event.accept()
                else:
                    event.ignore()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
