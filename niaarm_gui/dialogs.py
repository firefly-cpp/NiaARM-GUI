import os
import pandas as pd
from PyQt6.QtCore import Qt, QTimer, QLocale
from PyQt6.QtGui import QDoubleValidator, QMovie
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, QCheckBox, QPushButton, QMessageBox, \
    QLineEdit, QScrollArea, QWidget, QFrame, QProgressDialog
from niaarm_gui.antecedent_consequent_display import clean_rule_text, split_attributes
from niaarm_gui.models import StrictIntValidator


class LoadingDialog(QDialog):
    """Modal window for progression of mining"""

    def __init__(self, text="Mining in progress...", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Loading")
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint)
        self.setFixedSize(250, 300)
        self.setStyleSheet("background-color: white; color: black;")

        self.cancelled = False

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)

        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 14px; color: #2c3e50; font-weight: bold;")
        layout.addWidget(self.label)

        self.squash_info_label = QLabel("")
        self.squash_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.squash_info_label.setStyleSheet("font-size: 11px; color: #7f8c8d;")
        self.squash_info_label.setVisible(False)
        layout.addWidget(self.squash_info_label)

        self.progress_info_label = QLabel("")
        self.progress_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_info_label.setStyleSheet("font-size: 11px; color: #7f8c8d;")
        layout.addWidget(self.progress_info_label)

        self.spinner = QLabel()
        self.movie = QMovie("niaarm_gui/resources/spinner.gif")
        self.spinner.setMovie(self.movie)
        self.spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.spinner)
        self.movie.start()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.cancel_button.clicked.connect(self.__on_cancel)
        layout.addWidget(self.cancel_button)

    def __on_cancel(self):
        """Handles cancel button click"""
        reply = QMessageBox.question(
            self,
            "Cancel Mining",
            "Are you sure you want to cancel the mining process?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.cancelled = True
            self.label.setText("Cancelling...")
            self.cancel_button.setEnabled(False)
            self.reject()

    def set_text(self, text: str):
        self.label.setText(text)

    def set_squash_info(self, original: int, squashed: int):
        reduction = (1 - squashed / original) * 100
        self.squash_info_label.setText(f"Data Squashed: {original} → {squashed} elements ({reduction:.1f}%)")
        self.squash_info_label.setVisible(True)

    def show_completed(self):
        self.movie.stop()
        self.spinner.clear()
        self.cancel_button.setVisible(False)
        self.label.setText("✅ Mining completed!")
        QTimer.singleShot(2000, self.accept)

    def is_cancelled(self):
        """Returns True if user cancelled the operation"""
        return self.cancelled


class ProgressDialog(QProgressDialog):
    """Modal window with progress bar"""

    def __init__(self, message, max_value, parent=None):
        super().__init__(message, "Cancel", 0, max_value, None)

        self.setWindowTitle("Loading")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumDuration(0)

        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint
        )

        self.__apply_styles()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet("""
                    QPushButton {
                        background-color: #e74c3c;
                        color: white;
                        padding: 8px 16px;
                        border-radius: 4px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #c0392b;
                    }
                """)

        self.setCancelButton(self.cancel_button)

    def __apply_styles(self):
        self.setStyleSheet("""
            QProgressDialog {
                background-color: #f8f9fa;
                min-width: 400px;
                border: 1px solid #dee2e6;
            }
            QLabel {
                font-size: 14px;
                color: #2c3e50;
                margin-bottom: 10px;
                font-weight: bold;
            }
            QProgressBar {
                border: 1px solid #ced4da;
                border-radius: 8px;
                text-align: center;
                background-color: #e9ecef;
                height: 25px;
                color: #2c3e50;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, 
                                                 stop: 0 #4facfe, stop: 1 #00f2fe);
                border-radius: 7px;
            }
            QPushButton {
                background-color: #6c757d;
                color: white;
                border-radius: 4px;
                padding: 6px 15px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)


class DatasetInfoDialog(QDialog):
    """Dialog for displaying dataset statistics"""

    def __init__(self, csv_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Dataset Info — {os.path.basename(csv_path)}")
        self.setGeometry(100, 80, 700, 600)
        self.setStyleSheet("background-color: #f5f6fa;")

        df = pd.read_csv(csv_path)

        numerical_cols = df.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols = df.select_dtypes(include=["object"]).columns.tolist()

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel(f"Dataset — {os.path.basename(csv_path)}")
        title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #2c3e50;
            padding: 10px;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none;")
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)

        # === Overview card ===
        overview_card = self.__create_card("Overview", [
            ("Rows", str(len(df))),
            ("Total attributes", str(len(df.columns))),
            ("Numerical attributes", str(len(numerical_cols))),
            ("Categorical attributes", str(len(categorical_cols)))
        ], "#3498db")
        scroll_layout.addWidget(overview_card)

        # === Numerical attributes card ===
        if numerical_cols:
            num_data = []
            for col in numerical_cols:
                min_val = round(df[col].min(), 4)
                max_val = round(df[col].max(), 4)
                num_data.append((col, f"min = {min_val}\nmax = {max_val}"))
            num_card = self.__create_card("Numerical Attributes", num_data, "#2ecc71", True)
            scroll_layout.addWidget(num_card)

        # === Categorical attributes card ===
        if categorical_cols:
            cat_data = []
            for col in categorical_cols:
                categories = df[col].dropna().unique().tolist()
                if len(categories) > 10:
                    display = ", ".join(str(c) for c in categories[:10]) + ", ..."
                else:
                    display = ", ".join(str(c) for c in categories)
                cat_data.append((col, display))
            cat_card = self.__create_card(
                "Categorical Attributes", cat_data, "#e74c3c", True)
            scroll_layout.addWidget(cat_card)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #2c3e50; }
        """)
        close_btn.setFixedHeight(40)
        close_btn.clicked.connect(self.close)
        main_layout.addWidget(close_btn)

    def __create_card(self, title, data_pairs, accent_color, multiline=False):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #dfe6e9;
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)
        card_layout.setContentsMargins(20, 15, 20, 15)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {accent_color};
            padding-bottom: 5px;
            border-bottom: 2px solid {accent_color};
        """)
        card_layout.addWidget(title_label)

        data_widget = QWidget()
        data_layout = QVBoxLayout(data_widget)
        data_layout.setSpacing(8)
        data_layout.setContentsMargins(0, 10, 0, 0)

        for label_text, value_text in data_pairs:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            label = QLabel(label_text + ":")
            label.setStyleSheet("""
                font-weight: bold;
                color: #2c3e50;
                font-size: 13px;
            """)
            label.setFixedWidth(200)
            label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

            value = QLabel(value_text)
            value.setStyleSheet("""
                color: #34495e;
                font-size: 13px;
                font-family: monospace;
                background-color: #f8f9fa;
            """)
            value.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse)
            value.setWordWrap(multiline)
            value.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

            value.setFixedWidth(350)

            row_layout.addWidget(label)
            row_layout.addWidget(value)
            row_layout.addStretch()
            data_layout.addWidget(row_widget)

        card_layout.addWidget(data_widget)
        return card


class MetricSelectionDialog(QDialog):
    """Dialog for the selection of metrics for chosen plot"""
    def __init__(self, plot_type="scatter", parent=None):
        super().__init__(parent)
        self.setGeometry(200, 200, 400, 250)
        self.plot_type = plot_type

        if plot_type == "scatter":
            self.setWindowTitle("Select Metrics for Scatter Plot")
            self.instruction_text = "Select up to 2 additional metrics besides Lift:"
            self.available_metrics = [
                "support", "confidence", "coverage", "rhs_support", "conviction", "amplitude", "inclusion",
                "interestingness", "comprehensibility", "netconf", "yulesq", "zhang"
            ]
            self.metric1_default = "support"
            self.metric2_default = "confidence"
            self.label1_text = "Metric 1:"
            self.label2_text = "Metric 2:"
        else:  # two_key
            self.setWindowTitle("Select Metrics for Two-Key Plot")
            self.instruction_text = "Select 2 metrics for the two-key plot:"
            self.available_metrics = [
                "support", "confidence", "lift", "coverage", "rhs_support", "conviction", "amplitude", "inclusion",
                "interestingness", "comprehensibility", "netconf", "yulesq", "zhang"
            ]
            self.metric1_default = "support"
            self.metric2_default = "confidence"
            self.label1_text = "Key 1:"
            self.label2_text = "Key 2:"

        self.__setup_ui()

    def __setup_ui(self):
        """Sets up the UI elements"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Instructions
        instruction_label = QLabel(self.instruction_text)
        instruction_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        layout.addWidget(instruction_label)

        # Metric 1
        metric1_layout = QHBoxLayout()
        metric1_label = QLabel(self.label1_text)
        metric1_label.setFixedWidth(80)
        self.metric1_combo = QComboBox()
        self.metric1_combo.addItems(self.available_metrics)
        self.metric1_combo.setCurrentText(self.metric1_default)
        self.metric1_combo.setStyleSheet("background-color: white;")
        metric1_layout.addWidget(metric1_label)
        metric1_layout.addWidget(self.metric1_combo)
        layout.addLayout(metric1_layout)

        # Metric 2
        metric2_layout = QHBoxLayout()
        metric2_label = QLabel(self.label2_text)
        metric2_label.setFixedWidth(80)
        self.metric2_combo = QComboBox()
        self.metric2_combo.addItems(self.available_metrics)
        self.metric2_combo.setCurrentText(self.metric2_default)
        self.metric2_combo.setStyleSheet("background-color: white;")
        metric2_layout.addWidget(metric2_label)
        metric2_layout.addWidget(self.metric2_combo)
        layout.addLayout(metric2_layout)

        # Checkbox for interactivity
        self.interactive_checkbox = QCheckBox("Interactive plot")
        self.interactive_checkbox.setChecked(True)  # Privzeto označeno
        self.interactive_checkbox.setStyleSheet("font-size: 12px; padding: 5px;")
        layout.addWidget(self.interactive_checkbox)

        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")

        ok_btn.setStyleSheet(
            "background-color: #27ae60; color: white; padding: 8px 16px; "
            "border-radius: 4px; font-weight: bold;"
        )
        cancel_btn.setStyleSheet(
            "background-color: #e74c3c; color: white; padding: 8px 16px; "
            "border-radius: 4px; font-weight: bold;"
        )

        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    def get_selected_metrics(self):
        """Gets tuple of selected metrics"""
        metric1 = self.metric1_combo.currentText()
        metric2 = self.metric2_combo.currentText()

        if metric1 == metric2:
            QMessageBox.warning(self, "Warning", "Please select different metrics!")
            return None

        # For scatter always add lift
        if self.plot_type == "scatter":
            return (metric1, metric2, "lift")
        else:  # two_key
            return (metric1, metric2)

    def is_interactive(self):
        """Returs value of interactive checkbox"""
        return self.interactive_checkbox.isChecked()


class KValueSelectionDialog(QDialog):
    """Dialog for the selection of k value for grouped matrix plot"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("K Value Selection Dialog")
        self.setGeometry(200, 200, 400, 250)
        self.__setup_ui()

    def __setup_ui(self):
        """Sets up the UI elements"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Instruction
        instruction_label = QLabel("Configure Grouped Matrix Plot:")
        instruction_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        layout.addWidget(instruction_label)

        # K Value
        k_layout = QHBoxLayout()
        k_label = QLabel("Groups (k):")
        k_label.setFixedWidth(100)
        k_label.setStyleSheet("font-size: 12px;")
        self.k_input = QLineEdit("5")
        self.k_input.setValidator(StrictIntValidator(1, 100))
        self.k_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                color: black;
                border: 1px solid #bdc3c7;
                padding: 5px;
                border-radius: 3px;
            }
        """)
        self.k_input.setToolTip("Number of groups for antecedents (recommended: 3-10)")
        k_layout.addWidget(k_label)
        k_layout.addWidget(self.k_input)
        layout.addLayout(k_layout)

        # Checkbox for interactivity
        self.interactive_checkbox = QCheckBox("Interactive plot")
        self.interactive_checkbox.setChecked(True)
        self.interactive_checkbox.setStyleSheet("font-size: 12px; padding: 5px;")
        layout.addWidget(self.interactive_checkbox)

        button_layout = QHBoxLayout()

        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet(
            "background-color: #27ae60; color: white; padding: 8px 16px; "
            "border-radius: 4px; font-weight: bold;"
        )
        ok_btn.clicked.connect(self.accept)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(
            "background-color: #e74c3c; color: white; padding: 8px 16px; "
            "border-radius: 4px; font-weight: bold;"
        )
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def get_k(self):
        """Gets k value"""
        try:
            return int(self.k_input.text())
        except ValueError:
            return 5

    def is_interactive(self):
        """Returs value of interactive checkbox"""
        return self.interactive_checkbox.isChecked()


class RuleDetailsDialog(QDialog):
    """Dialog for the details of selected rule"""

    def __init__(self, rule, row_number, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Rule Details - Rule #{row_number + 1}")
        self.setGeometry(100, 80, 700, 700)
        self.setStyleSheet("background-color: #f5f6fa;")

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel(f"Rule #{row_number + 1} - Detailed Information")
        title_label.setStyleSheet("""
            font-size: 20px; 
            font-weight: bold; 
            color: #2c3e50;
            padding: 10px;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none;")
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)

        antecedent_clean = self._format_rule_for_display(str(rule.antecedent))
        consequent_clean = self._format_rule_for_display(str(rule.consequent))

        # === Rule Structure ===
        structure_card = self.__create_card("Rule Structure", [
            ("Antecedent", antecedent_clean),
            ("Consequent", consequent_clean)
        ], "#3498db", multiline=True)
        scroll_layout.addWidget(structure_card)

        # === Metrics ===
        basic_card = self.__create_card("Metrics", [
            ("Fitness", f"{rule.fitness:.3f}"),
            ("Support", f"{rule.support:.3f}"),
            ("Confidence", f"{rule.confidence:.3f}"),
            ("Lift", f"{rule.lift:.3f}"),
            ("Coverage", f"{rule.coverage:.3f}"),
            ("RHS Support", f"{rule.rhs_support:.3f}"),
            ("Conviction", f"{rule.conviction:.3f}"),
            ("Interestingness", f"{rule.interestingness:.3f}"),
            ("Amplitude", f"{rule.amplitude:.3f}"),
            ("Inclusion", f"{rule.inclusion:.3f}"),
            ("Comprehensibility", f"{rule.comprehensibility:.3f}"),
            ("Netconf", f"{rule.netconf:.3f}"),
            ("Yule's Q", f"{rule.yulesq:.3f}"),
            ("Zhang", f"{rule.zhang:.3f}")
        ], "#2ecc71")
        scroll_layout.addWidget(basic_card)

        # === Transaction Counts ===
        transaction_card = self.__create_card("Transaction Counts", [
            ("Total Transactions", str(rule.num_transactions)),
            ("Antecedent Count", str(rule.antecedent_count)),
            ("Consequent Count", str(rule.consequent_count)),
            ("Both (A ∩ C)", str(rule.full_count)),
            ("A but not C (A - C)", str(rule.ant_not_con)),
            ("C but not A (C - A)", str(rule.con_not_ant)),
            ("Neither (¬A ∩ ¬C)", str(rule.not_ant_not_con))
        ], "#e74c3c")
        scroll_layout.addWidget(transaction_card)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495e; 
                color: white; 
                padding: 10px 20px; 
                border-radius: 6px; 
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2c3e50;
            }
        """)
        close_btn.clicked.connect(self.close)
        close_btn.setFixedHeight(40)
        main_layout.addWidget(close_btn)

    def _format_rule_for_display(self, rule_text):
        """Formats the rule for display"""
        cleaned = clean_rule_text(rule_text)
        attributes = split_attributes(cleaned)
        return '\n'.join(attributes)

    def __create_card(self, title, data_pairs, accent_color, multiline=False):
        """Creates QFrame card for display of the rule"""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 10px;
                border: 1px solid #dfe6e9;
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)
        card_layout.setContentsMargins(20, 15, 20, 15)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {accent_color};
            padding-bottom: 5px;
            border-bottom: 2px solid {accent_color};
        """)
        card_layout.addWidget(title_label)

        data_widget = QWidget()
        data_layout = QVBoxLayout(data_widget)
        data_layout.setSpacing(8)
        data_layout.setContentsMargins(0, 10, 0, 0)

        for label_text, value_text in data_pairs:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            # Name of metric/attribute
            label = QLabel(label_text + ":")
            label.setStyleSheet("""
                font-weight: bold;
                color: #2c3e50;
                font-size: 13px;
            """)
            label.setFixedWidth(200)
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

            # Value
            value = QLabel(value_text)
            value.setStyleSheet("""
                color: #34495e;
                font-size: 13px;
                font-family: monospace;
                background-color: #f8f9fa;
            """)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

            if multiline:
                value.setWordWrap(True)
                value.setMinimumWidth(400)
                value.setMaximumWidth(400)
            else:
                value.setFixedWidth(250)

            value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

            row_layout.addWidget(label)
            row_layout.addWidget(value)
            row_layout.addStretch()

            data_layout.addWidget(row_widget)

        card_layout.addWidget(data_widget)
        return card


class FilterDialog(QDialog):
    """Dialog for configuration of filters"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filter Rules")
        self.setGeometry(100, 100, 500, 600)
        self.setStyleSheet("background-color: #ebf1f5;")

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("Set Minimum Thresholds for Metrics")
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
            padding: 10px;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none;")
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)

        self.metric_inputs = {}
        metrics = [
            ("Fitness", "fitness", 0.0, 1.0),
            ("Support", "support", 0.0, 1.0),
            ("Confidence", "confidence", 0.0, 1.0),
            ("Lift", "lift", 0.0, 10.0),
            ("Coverage", "coverage", 0.0, 1.0),
            ("RHS Support", "rhs_support", 0.0, 1.0),
            ("Conviction", "conviction", 0.0, 10.0),
            ("Interestingness", "interestingness", 0.0, 1.0),
            ("Comprehensibility", "comprehensibility", 0.0, 1.0),
            ("Netconf", "netconf", -1.0, 1.0),
            ("Yule's Q", "yulesq", -1.0, 1.0),
            ("Zhang", "zhang", -1.0, 1.0)
        ]

        for display_name, attr_name, min_val, max_val in metrics:
            metric_frame = QFrame()
            metric_frame.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 1px solid #dfe6e9;
                    border-radius: 5px;
                    padding: 10px;
                }
            """)
            metric_layout = QHBoxLayout(metric_frame)

            # Checkbox
            checkbox = QCheckBox(display_name)
            checkbox.setStyleSheet("""
                QCheckBox {
                    color: black;
                    background-color: white;
                }
                QCheckBox::indicator:unchecked {
                    border: 1px solid #95a5a6;
                    background-color: white;
                    border-radius: 3px;
                }
            """)
            metric_layout.addWidget(checkbox)

            # Input field
            input_field = QLineEdit()
            input_field.setPlaceholderText(f"Min: {min_val}")
            input_field.setText(str(min_val))
            input_field.setEnabled(False)
            input_field.setStyleSheet("""
                QLineEdit {
                    padding: 5px;
                    border: 1px solid #bdc3c7;
                    border-radius: 3px;
                }
                QLineEdit:disabled {
                    background-color: #ecf0f1;
                }
            """)
            input_field.setFixedWidth(100)

            # Validator
            input_field.setValidator(QDoubleValidator(min_val, max_val, 3))
            input_field.validator().setNotation(QDoubleValidator.Notation.StandardNotation)
            input_field.validator().setLocale(QLocale(QLocale.Language.English))

            metric_layout.addWidget(input_field)

            # Enable/disable input based on checkbox
            checkbox.stateChanged.connect(
                lambda state, inp=input_field: inp.setEnabled(state == Qt.CheckState.Checked.value)
            )

            scroll_layout.addWidget(metric_frame)

            self.metric_inputs[attr_name] = (checkbox, input_field)

        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        button_layout = QHBoxLayout()

        apply_btn = QPushButton("Apply Filter")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        apply_btn.clicked.connect(self.accept)

        reset_btn = QPushButton("Reset")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
        """)
        reset_btn.clicked.connect(self.reset_filters)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(apply_btn)
        button_layout.addWidget(reset_btn)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def reset_filters(self):
        """Resets all the filters"""
        for checkbox, input_field in self.metric_inputs.values():
            checkbox.setChecked(False)
            input_field.setText("0.0")

    def get_filters(self):
        """Gets dictionary of selected filters"""
        filters = {}
        for attr_name, (checkbox, input_field) in self.metric_inputs.items():
            if checkbox.isChecked():
                try:
                    value = float(input_field.text())
                    filters[attr_name] = value
                except ValueError:
                    pass
        return filters