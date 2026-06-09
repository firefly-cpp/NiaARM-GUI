from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QHBoxLayout, QScrollArea, QWidget, QMessageBox, QTableWidget,
    QTableWidgetItem, QFrame, QGroupBox, QGridLayout, QCheckBox, QMainWindow, QFileDialog)
import pandas as pd
import csv
import openpyxl
from niaarm import RuleList
from niaarm.visualize import scatter_plot, grouped_matrix_plot, two_key_plot
from niaarm_gui.antecedent_consequent_display import clean_rule_text
from niaarm_gui.dialogs import (
    MetricSelectionDialog, KValueSelectionDialog, RuleDetailsDialog, FilterDialog, ProgressDialog)
from niaarm_gui.models import NumericTableWidgetItem, LoadedRule


class MiningResultsViewer(QMainWindow):
    def __init__(self, rules=None, file_path=None, time=None):
        super().__init__()
        self.setWindowTitle("Mining Results Viewer")
        self.setGeometry(50, 50, 1000, 700)
        self.setStyleSheet("background-color: #ebf1f5; color:black")

        # Global variables used in multiple methods inside the class
        self.rules = None
        self.filtered_rules = None
        self.time = time
        self.active_filters = {}
        self.file_path = file_path
        self.column_checkboxes = {}

        if file_path is None:
            self.rules = rules

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)

        self.__create_menu_bar()
        self.__create_status_bar()

        control_panel = self.__create_control_panel()
        main_layout.addWidget(control_panel)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(16)
        self.rules_table.setHorizontalHeaderLabels([
            "Antecedent", "Consequent", "Fitness", "Support", "Confidence", "Lift",
            "Coverage", "RHS Support", "Conviction", "Amplitude", "Inclusion", "Interestingness",
            "Comprehensibility", "Netconf", "Yule's Q", "Zhang"
        ])

        self.rules_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.rules_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.rules_table.setAlternatingRowColors(True)
        self.rules_table.setStyleSheet("background-color: white; color: black;")
        self.rules_table.horizontalHeader().setStretchLastSection(False)

        self.__toggle_column_visibility()
        self.rules_table.doubleClicked.connect(self.__on_row_double_clicked)

        header = self.rules_table.horizontalHeader()
        header.setMinimumSectionSize(100)
        header.sectionClicked.connect(
            lambda _: self.rules_table.resizeColumnsToContents()
        )

        scroll_layout.addWidget(self.rules_table)

        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        self.__load_rules()

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
        save_action.triggered.connect(self.__save_file)
        file_menu.addAction(save_action)

        # Save As action
        save_as_action = QAction("Save As...", self)
        save_as_action.triggered.connect(self.__save_file_as)
        file_menu.addAction(save_as_action)

        # Export to Excel action
        export_excel_action = QAction("Export to Excel", self)
        export_excel_action.triggered.connect(self.__export_to_excel)
        file_menu.addAction(export_excel_action)

        file_menu.addSeparator()

        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menu_bar.addMenu("Tools")

        # Filter rules action
        filter_rules_action = QAction("Filter rules", self)
        filter_rules_action.triggered.connect(self.__filter_rules)
        tools_menu.addAction(filter_rules_action)

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
        if self.time is not None:
            status_bar.showMessage(f"Run time: {self.time:.2f}s")
        else:
            status_bar.showMessage(f"Loaded from: {self.file_path}")

    def __create_control_panel(self):
        """Creates control panel above the table"""
        control_panel = QFrame()
        control_panel.setFrameShape(QFrame.Shape.StyledPanel)
        control_panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #dfe6e9;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        main_layout = QHBoxLayout(control_panel)
        main_layout.setSpacing(20)

        # === SECTION 1: Columns ===
        columns_group = QGroupBox("Visible Columns")
        columns_group.setStyleSheet("""
            QGroupBox {
                background-color: #ebf1f5;
                font-weight: bold;
                color: black;
                border: 2px solid #3498db;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                color: black;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        columns_layout = QGridLayout()
        columns_layout.setSpacing(5)

        columns = [
            "Fitness", "Support", "Confidence", "Lift", "Coverage",
            "RHS Support", "Conviction", "Amplitude", "Inclusion", "Interestingness",
            "Comprehensibility", "Netconf", "Yule's Q", "Zhang"
        ]

        for i, col in enumerate(columns):
            checkbox = QCheckBox(col)
            checkbox.setStyleSheet("""
                QCheckBox {
                    color: black;
                }
                QCheckBox::indicator:unchecked {
                    border: 1px solid #95a5a6;
                    background-color: white;
                    border-radius: 3px;
                }
            """)
            if i < 5:
                checkbox.setChecked(True)

            checkbox.stateChanged.connect(self.__toggle_column_visibility)
            self.column_checkboxes[col] = checkbox

            row = i // 5
            col_pos = i % 5
            columns_layout.addWidget(checkbox, row, col_pos)

        columns_group.setLayout(columns_layout)
        main_layout.addWidget(columns_group, stretch=2)

        # === SEPARATOR ===
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setLineWidth(2)
        separator.setStyleSheet("color: #bdc3c7;")
        main_layout.addWidget(separator)

        # === SECTION 2: Visualization ===
        viz_group = QGroupBox("Visualizations")
        viz_group.setStyleSheet("""
            QGroupBox {
                background-color: #ebf1f5;
                font-weight: bold;
                color: black;
                border: 2px solid #2ecc71;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                color: black;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        viz_layout = QGridLayout()
        viz_layout.setSpacing(8)

        scatter_btn = QPushButton("Scatter Plot")
        matrix_btn = QPushButton("Matrix Plot")
        two_key_btn = QPushButton("Two-Key Plot")

        for btn in [scatter_btn, matrix_btn, two_key_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    padding: 8px 15px;
                    border-radius: 5px;
                    font-weight: bold;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)

        viz_layout.addWidget(scatter_btn, 0, 0)
        viz_layout.addWidget(matrix_btn, 1, 0)
        viz_layout.addWidget(two_key_btn, 0, 1)

        viz_group.setLayout(viz_layout)
        main_layout.addWidget(viz_group, stretch=1)

        scatter_btn.clicked.connect(self.__show_scatter_plot)
        matrix_btn.clicked.connect(self.__show_matrix_plot)
        two_key_btn.clicked.connect(self.__show_two_key_plot)

        return control_panel

    def __load_rules(self):
        """Loads rules from either csv file or the rules that were just mined through self.rules"""
        self.rules_table.setSortingEnabled(False)

        try:
            if self.rules is None:
                self.rules = self.__get_rules_from_csv()

            if len(self.rules) > 0:
                self.filtered_rules = list(self.rules)
                self.__update_table()

        except Exception:
            QMessageBox.critical(self, "Error", f"Unable to load rules")

    def __save_file(self):
        """Saves rules into existing CSV file (current location)"""
        if self.file_path:
            self.__save_to_csv(self.file_path)
        else:
            self.__save_file_as()

    def __save_file_as(self):
        """Saves rules in a new CSV file"""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Mining Results",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )

        if file_name:
            if not file_name.endswith('.csv'):
                file_name += '.csv'

            self.__save_to_csv(file_name)
            self.file_path = file_name
            self.setWindowTitle(f"Mining Results Viewer - {file_name}")

    def __save_to_csv(self, file_path):
        """Saves current sorted rules that are visible in the table at the time of saving"""
        sorted_rules = self.__get_current_sorted_rules()
        num_rules = len(sorted_rules)

        progress = None
        if num_rules > 1000:
            progress = ProgressDialog("Saving rules to CSV...", num_rules)
            progress.setValue(0)
            progress.show()

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                writer.writerow([
                    "antecedent", "consequent", "fitness", "num_transactions",
                    "antecedent_count", "consequent_count", "full_count",
                    "ant_not_con", "con_not_ant", "not_ant_not_con",
                    "inclusion", "amplitude"
                ])

                for i, rule in enumerate(sorted_rules):
                    writer.writerow([
                        rule.antecedent, rule.consequent, rule.fitness,
                        rule.num_transactions, rule.antecedent_count,
                        rule.consequent_count, rule.full_count,
                        rule.ant_not_con, rule.con_not_ant,
                        rule.not_ant_not_con, rule.inclusion, rule.amplitude
                    ])

                    if progress:
                        progress.setValue(i)
                        if progress.wasCanceled():
                            return

                if progress:
                    progress.setValue(num_rules)
                    progress.close()

                QMessageBox.information(self, "Success", f"Results saved to:\n{file_path}")

        except Exception as e:
            if progress:
                progress.close()
            QMessageBox.critical(self, "Error", f"Failed to save file:\n{str(e)}")

    def __export_to_excel(self):
        file_name, _ = QFileDialog.getSaveFileName(
        self, "Export to Excel", "", "Excel Files (*.xlsx);;All Files (*)")

        if not file_name:
            return
        if not file_name.endswith(".xlsx"):
            file_name += ".xlsx"

        sorted_rules = self.__get_current_sorted_rules()
        num_rules = len(sorted_rules)

        progress = None
        if num_rules > 1000:
            progress = ProgressDialog("Exporting rules to Excel...", num_rules)
            progress.setValue(0)
            progress.show()

        try:
            wb = openpyxl.Workbook()
            ws = wb.active

            headers = [
                "Antecedent", "Consequent", "Fitness", "Support", "Confidence",
                "Lift", "Coverage", "RHS Support", "Conviction", "Amplitude",
                "Inclusion", "Interestingness", "Comprehensibility",
                "Netconf", "Yule's Q", "Zhang"
            ]
            ws.append(headers)

            for i, rule in enumerate(sorted_rules):
                ws.append([
                    clean_rule_text(str(rule.antecedent)),
                    clean_rule_text(str(rule.consequent)),
                    rule.fitness, rule.support, rule.confidence,
                    rule.lift, rule.coverage, rule.rhs_support,
                    rule.conviction, rule.amplitude, rule.inclusion,
                    rule.interestingness, rule.comprehensibility,
                    rule.netconf, rule.yulesq, rule.zhang
                ])

                if progress:
                    progress.setValue(i)
                    if progress.wasCanceled():
                        return

            wb.save(file_name)

            if progress:
                progress.setValue(num_rules)
                progress.close()

            self.statusBar().showMessage(f"Exported to Excel: {file_name}", 5000)
            QMessageBox.information(self, "Success", f"Results exported to:\n{file_name}")

        except Exception as e:
            if progress:
                progress.close()
            QMessageBox.critical(self, "Error", f"Failed to export to Excel:\n{str(e)}")

    def __filter_rules(self):
        """Filters rules in the table with metrics thresholds selected in FilterDialog"""
        if self.rules is None:
            QMessageBox.warning(self, "Warning", "No rules to filter!")
            return

        dialog = FilterDialog(self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            filters = dialog.get_filters()

            if not filters:
                self.filtered_rules = list(self.rules)
                self.active_filters = {}
            else:
                self.active_filters = filters
                self.filtered_rules = []

                for rule in self.rules:
                    passes_filter = True

                    for metric, min_value in filters.items():
                        rule_value = getattr(rule, metric, None)

                        if rule_value is None or rule_value < min_value:
                            passes_filter = False
                            break

                    if passes_filter:
                        self.filtered_rules.append(rule)

            self.__update_table()

            # Show status of rules
            if self.active_filters:
                filter_text = ", ".join([f"{k} ≥ {v}" for k, v in self.active_filters.items()])
                QMessageBox.information(
                    self,
                    "Filter Applied",
                    f"Showing {len(self.filtered_rules)} of {len(self.rules)} rules\n\n"
                    f"Active filters: {filter_text}"
                )
            else:
                QMessageBox.information(
                    self,
                    "Filter Cleared",
                    f"Showing all {len(self.rules)} rules"
                )

    def __update_table(self):
        """Updates/Fills the table with filtered_rules"""
        self.rules_table.setSortingEnabled(False)
        self.rules_table.setUpdatesEnabled(False)
        self.rules_table.setRowCount(0)

        if self.filtered_rules is None:
            return

        num_rules = len(self.filtered_rules)

        progress = None
        if num_rules > 100:
            progress = ProgressDialog("Loading rules for display...", num_rules)
            progress.setValue(0)
            progress.show()

        self.rules_table.setRowCount(len(self.filtered_rules))

        for i, rule in enumerate(self.filtered_rules):
            if progress and i % 10 == 0:
                progress.setValue(i)
                if progress.wasCanceled():
                    self.rules_table.setRowCount(0)
                    self.rules_table.setUpdatesEnabled(True)
                    self.rules = None
                    return

            try:
                original_index = self.rules.index(rule)
            except ValueError:
                original_index = i

            antecedent_clean = clean_rule_text(str(rule.antecedent))
            consequent_clean = clean_rule_text(str(rule.consequent))

            antecedent_item = QTableWidgetItem(antecedent_clean)
            antecedent_item.setData(Qt.ItemDataRole.UserRole, original_index)
            self.rules_table.setItem(i, 0, antecedent_item)

            consequent_item = QTableWidgetItem(consequent_clean)
            consequent_item.setData(Qt.ItemDataRole.UserRole, original_index)
            self.rules_table.setItem(i, 1, consequent_item)

            for col, attr in enumerate([
                'fitness', 'support', 'confidence', 'lift', 'coverage',
                'rhs_support', 'conviction', 'amplitude', 'inclusion',
                'interestingness', 'comprehensibility', 'netconf', 'yulesq', 'zhang'
            ], start=2):
                item = NumericTableWidgetItem(getattr(rule, attr))
                item.setData(Qt.ItemDataRole.UserRole, original_index)
                self.rules_table.setItem(i, col, item)

        if progress:
            progress.setValue(num_rules)
            progress.close()

        self.rules_table.setUpdatesEnabled(True)
        self.rules_table.setSortingEnabled(True)
        self.rules_table.resizeColumnsToContents()

    def __get_rules_from_csv(self):
        """Gets rules from csv file with LoadedRule class"""
        rule_list = RuleList()
        df = pd.read_csv(self.file_path)
        num_rules = len(df)

        progress = None
        if num_rules > 1000:
            progress = ProgressDialog("Loading rules from CSV file...", num_rules)
            progress.setValue(0)
            progress.show()

        for row_idx, row in df.iterrows():
            if progress and row_idx % 10 == 0:
                progress.setValue(row_idx)
                if progress.wasCanceled():
                    rule_list.clear()
                    break

            rule = LoadedRule(
                antecedent=row["antecedent"],
                consequent=row["consequent"],
                fitness=row["fitness"],
                num_transactions=row["num_transactions"],
                loaded_inclusion=row["inclusion"],
                loaded_amplitude=row["amplitude"],
                full_count=row["full_count"],
                antecedent_count=row["antecedent_count"],
                consequent_count=row["consequent_count"],
                ant_not_con=row["ant_not_con"],
                con_not_ant=row["con_not_ant"],
                not_ant_not_con=row["not_ant_not_con"]
            )

            rule_list.append(rule)

        if progress:
            progress.setValue(num_rules)
            progress.close()

        return rule_list

    def __get_current_sorted_rules(self):
        """Gets current sorted rules from the table"""
        sorted_rules = RuleList()

        for row in range(self.rules_table.rowCount()):
            item = self.rules_table.item(row, 0)
            if item is not None:
                original_index = item.data(Qt.ItemDataRole.UserRole)
                if original_index is not None and original_index < len(self.rules):
                    sorted_rules.append(self.rules[original_index])

        return sorted_rules

    def __toggle_column_visibility(self):
        """Shows/Hides columns depending on checkbox selection in Control Panel"""
        column_mapping = {
            "Fitness": 2, "Support": 3, "Confidence": 4, "Lift": 5,
            "Coverage": 6, "RHS Support": 7, "Conviction": 8, "Amplitude": 9,
            "Inclusion": 10, "Interestingness": 11, "Comprehensibility": 12,
            "Netconf": 13, "Yule's Q": 14, "Zhang": 15
        }

        for col_name, checkbox in self.column_checkboxes.items():
            col_index = column_mapping[col_name]
            if checkbox.isChecked():
                self.rules_table.showColumn(col_index)
            else:
                self.rules_table.hideColumn(col_index)

    def __on_row_double_clicked(self, index):
        """Shows details of the selected rule in RuleDetailsDialog"""
        row = index.row()
        item = self.rules_table.item(row, 0)

        if item is not None:
            original_index = item.data(Qt.ItemDataRole.UserRole)

            if original_index is not None and original_index < len(self.rules):
                rule = self.rules[original_index]
                dialog = RuleDetailsDialog(rule, row, self)
                dialog.exec()

    def __show_scatter_plot(self):
        """Generates scatter plot with metrics selected in MetricSelectionDialog"""
        dialog = MetricSelectionDialog(plot_type="scatter", parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            metrics = dialog.get_selected_metrics()
            if metrics is None:
                return

            rules = self.__get_current_sorted_rules()
            interactive = dialog.is_interactive()

            try:
                fig = scatter_plot(rules=rules, metrics=metrics, interactive=interactive)
                fig.show()
            except Exception as e:
                QMessageBox.warning(self, "Visualization Error", f"Unable to display scatter plot:\n{e}")

    def __show_two_key_plot(self):
        """Generates two-key plot with metrics selected in MetricSelectionDialog"""
        dialog = MetricSelectionDialog(plot_type="two_key", parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            metrics = dialog.get_selected_metrics()
            if metrics is None:
                return

            rules = self.__get_current_sorted_rules()
            interactive = dialog.is_interactive()

            try:
                fig = two_key_plot(rules=rules, metrics=metrics,interactive=interactive)
                fig.show()
            except Exception:
                QMessageBox.warning(self, "Visualization Error", f"Unable to display two-key plot")

    def __show_matrix_plot(self):
        """Generates grouped matrix plot with k value selected in KValueSelectionDialog"""
        dialog = KValueSelectionDialog(parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            k = dialog.get_k()
            interactive = dialog.is_interactive()
            rules = self.__get_current_sorted_rules()
            metrics = ("support", "lift")

            try:
                fig = grouped_matrix_plot(rules=rules, metrics=metrics, k=k, interactive=interactive)
                fig.show()
            except Exception as e:
                QMessageBox.warning(self, "Visualization Error", f"Unable to display matrix plot:\n{e}")