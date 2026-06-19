import math
import os
import csv
import json
import time
import pandas as pd
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit, QComboBox, QPushButton,
    QFileDialog, QSlider, QTableWidget, QTableWidgetItem, QScrollArea, QMessageBox, QFrame)
from PyQt6.QtCore import Qt, QEvent, QObject, QThread, pyqtSignal
from niaarm import Dataset, squash, NiaARM
from niapy.task import OptimizationType, Task
from niapy.util.factory import get_algorithm
from niapy.callbacks import Callback
from niapy.algorithms.basic import (
    DifferentialEvolution, ParticleSwarmOptimization, GeneticAlgorithm, FireflyAlgorithm, BatAlgorithm)
from niaarm_gui.csv_viewer import CsvEditorWindow
from niaarm_gui.mining_results_viewer import MiningResultsViewer
from niaarm_gui.dialogs import LoadingDialog, DatasetInfoDialog
from niaarm_gui.models import StrictIntValidator, CheckBox


class NiaARMGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NiaARM GUI")
        self.setGeometry(50, 50, 1000, 700)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self.__create_menu_bar()
        self.__create_tool_bar()
        self.__create_status_bar()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(main_widget)
        self.setCentralWidget(scroll)

        layout = QVBoxLayout(main_widget)
        main_widget.setStyleSheet("background-color: #f0f4f8; color: black")

        label_style_sheet = "font-size: 14px; font-weight: bold; color: #2c3e50;"
        self.csv_editor = None
        self.mining_results_viewer_list: list[MiningResultsViewer] = []

        # GroupBox Section 1: CSV dataset configuration
        csv_group = self.__create_group_box("CSV dataset configuration")
        csv_hbox = QHBoxLayout()

        self.csv_input = QLineEdit()
        self.csv_input.setReadOnly(True)
        self.csv_input.setStyleSheet("background-color: white; color: black; border: 1px solid #bdc3c7; padding: 5px;")
        csv_hbox.addWidget(self.csv_input)

        self.csv_select_button = QPushButton("Select file")
        self.csv_select_button.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; padding: 5px; border-radius: 3px; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.csv_select_button.clicked.connect(self.__select_csv)
        csv_hbox.addWidget(self.csv_select_button)

        self.csv_view_button = QPushButton("Edit file")
        self.csv_view_button.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; padding: 5px; border-radius: 3px; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.csv_view_button.clicked.connect(self.__view_csv)
        csv_hbox.addWidget(self.csv_view_button)

        self.csv_info_button = QPushButton()
        self.csv_info_button.setIcon(QIcon("niaarm_gui/resources/info.png"))
        self.csv_info_button.setToolTip("Dataset Info")
        self.csv_info_button.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; padding: 5px; border-radius: 3px; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.csv_info_button.clicked.connect(self.__show_dataset_info)
        csv_hbox.addWidget(self.csv_info_button)

        csv_group.setLayout(csv_hbox)
        layout.addWidget(csv_group)

        layout.addWidget(self.__create_separator())

        # GroupBox Section 2: Data squashing configuration
        data_squash_group = self.__create_group_box("Data squashing configuration")

        # Data squashing yes/no
        data_squash_vbox = QVBoxLayout()
        self.data_squash_combo = QComboBox()
        self.data_squash_combo.addItems(["No", "Yes"])
        self.data_squash_combo.setStyleSheet(
            "background-color: white; color: black; border: 1px solid #bdc3c7; padding: 5px;")
        self.data_squash_combo.setToolTip(
            "Reduce dataset size by merging similar transactions"
        )
        data_squash_vbox.addWidget(self.data_squash_combo)
        self.data_squash_combo.currentIndexChanged.connect(self.__update_data_squashing_settings_visibility)

        # Similarity
        similarity_vbox = QVBoxLayout()
        self.similarity_label = QLabel("Similarity:")
        self.similarity_label.setStyleSheet(label_style_sheet)
        similarity_vbox.addWidget(self.similarity_label)
        self.similarity_combo = QComboBox()
        self.similarity_combo.setMinimumWidth(200)
        self.similarity_combo.addItems(
            ["Euclidean", "Cosine"])
        similarity_vbox.addWidget(self.similarity_combo)
        self.similarity_combo.setStyleSheet(
            "background-color: white; color: black; border: 1px solid #bdc3c7; padding: 5px;")

        # Threshold
        threshold_vbox = QVBoxLayout()
        self.threshold_label = QLabel("Threshold (0.0 - 1.0):")
        self.threshold_label.setStyleSheet(label_style_sheet)
        threshold_vbox.addWidget(self.threshold_label)

        # Slider threshold
        threshold_slider_hbox = QHBoxLayout()
        self.ds_threshold_value_label = QLabel("0.50")
        self.ds_threshold_value_label.setStyleSheet("color: #7f8c8d;")
        threshold_slider_hbox.addWidget(self.ds_threshold_value_label)
        self.ds_threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.ds_threshold_slider.setMinimum(0)
        self.ds_threshold_slider.setMaximum(104)
        self.ds_threshold_slider.setValue(52)  # actual value 0.50
        self.ds_threshold_slider.setStyleSheet(
            "QSlider::groove:horizontal { background: #bdc3c7; height: 8px; border-radius: 4px; }"
            "QSlider::handle:horizontal { background: #3498db; width: 18px; height: 18px; border-radius: 9px; }"
        )
        threshold_slider_hbox.addWidget(self.ds_threshold_slider)
        self.ds_threshold_slider.valueChanged.connect(
            lambda pos: self.ds_threshold_value_label.setText(
                f"{self.__slider_to_threshold(pos)[0]:.{self.__slider_to_threshold(pos)[1]}f}"
            )
        )
        threshold_vbox.addLayout(threshold_slider_hbox)

        similarity_threshold_hbox = QHBoxLayout()
        similarity_threshold_hbox.addLayout(similarity_vbox)
        similarity_threshold_hbox.addLayout(threshold_vbox)
        data_squash_vbox.addLayout(similarity_threshold_hbox)

        data_squash_group.setLayout(data_squash_vbox)
        layout.addWidget(data_squash_group)

        layout.addWidget(self.__create_separator())

        # GroupBox Section 3: Metrics configuration
        metrics_group = self.__create_group_box("Metrics configuration")

        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(4)
        self.metrics_table.setStyleSheet(
            "QTableWidget { background-color: white; color: black; border: 1px solid #bdc3c7; }"
        )
        self.metrics_table.setHorizontalHeaderLabels(["Metric", "Use", "Value", "Weight"])
        self.metrics_table.horizontalHeader().setStyleSheet("color: black;")
        self.metrics_table.setColumnWidth(0, 200)
        self.metrics_table.setColumnWidth(1, 50)
        self.metrics_table.setColumnWidth(2, 50)
        self.metrics_table.horizontalHeader().setStretchLastSection(True)
        self.metrics_table.setFixedHeight(266)
        self.metrics_table.setToolTip("Select metrics to optimize fitness and set their weight values")

        metrics = [
            "Support", "Confidence", "Coverage", "Interestingness",
            "Comprehensibility", "Amplitude", "Inclusion", "RHS Support"
        ]
        self.metrics_table.setRowCount(len(metrics))

        self.metric_sliders = {}

        for i, metric in enumerate(metrics):
            # metric name
            metric_item = QTableWidgetItem(metric)
            metric_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.metrics_table.setItem(i, 0, metric_item)

            # checkbox
            check_box = CheckBox()
            center_widget = QWidget()
            center_layout = QHBoxLayout(center_widget)
            center_layout.addWidget(check_box)
            center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            center_layout.setContentsMargins(0, 0, 0, 0)

            self.metrics_table.setCellWidget(i, 1, center_widget)

            # weight value
            value_label = QLabel("0.50")
            value_label.setStyleSheet("color: #7f8c8d; padding-left: 5px;")
            self.metrics_table.setCellWidget(i, 2, value_label)

            # weight slider
            weight_slider = QSlider(Qt.Orientation.Horizontal)
            weight_slider.setMinimum(1)
            weight_slider.setMaximum(100)
            weight_slider.setValue(50)
            weight_slider.setStyleSheet(
                "QSlider::groove:horizontal { background: #bdc3c7; height: 6px; border-radius: 3px; }"
                "QSlider::handle:horizontal { background: #3498db; width: 16px; height: 16px; border-radius: 8px; }"
            )
            self.metrics_table.setCellWidget(i, 3, weight_slider)

            weight_slider.valueChanged.connect(lambda value, lbl=value_label: lbl.setText(f"{value / 100:.2f}"))

            self.metric_sliders[metric] = (check_box, weight_slider, value_label)

        metrics_hbox = QHBoxLayout()
        metrics_hbox.addWidget(self.metrics_table)
        metrics_group.setLayout(metrics_hbox)
        layout.addWidget(metrics_group)

        layout.addWidget(self.__create_separator())

        # GroupBox Section 4: Algorithm
        algo_group = self.__create_group_box("Algorithm configuration")

        algo_vbox = QVBoxLayout()
        algo_hbox = QHBoxLayout()

        # Algorithm selection
        algorithm_vbox = QVBoxLayout()
        algo_label = QLabel("Algorithm:")
        algo_label.setStyleSheet(label_style_sheet)
        algorithm_vbox.addWidget(algo_label)
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(["Select Algorithm", "Differential Evolution", "Particle Swarm Optimization",
                                       "Genetic Algorithm", "Bat Algorithm", "Firefly Algorithm"])
        self.algorithm_combo.setStyleSheet("background-color: white; border: 1px solid #bdc3c7; padding: 5px;")
        self.algorithm_combo.setMinimumWidth(250)
        algorithm_vbox.addWidget(self.algorithm_combo)
        self.algorithm_combo.currentIndexChanged.connect(self.__update_algorithm_settings_visibility)
        self.algorithm_combo.setToolTip(
            "Choose the optimization algorithm for rule mining"
        )

        # Population Size
        pop_size_vbox = QVBoxLayout()
        pop_label = QLabel("Population Size:")
        pop_label.setStyleSheet(label_style_sheet)
        pop_size_vbox.addWidget(pop_label)
        self.pop_size_input = QLineEdit("50")
        self.pop_size_input.setValidator(StrictIntValidator(1, 1_000_000))
        self.pop_size_input.setStyleSheet("background-color: white; color: black; border: 1px solid #bdc3c7; padding: 5px;")
        pop_size_vbox.addWidget(self.pop_size_input)
        self.pop_size_input.setToolTip("Number of candidate solutions (recommended: 30-100)")

        # Max Iterations
        max_iter_vbox = QVBoxLayout()
        iter_header_hbox = QHBoxLayout()
        iter_header_hbox.setSpacing(2)
        iter_header_hbox.setContentsMargins(0, 0, 0, 0)
        iter_header_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.max_iter_checkbox = CheckBox()
        self.max_iter_checkbox.setChecked(True)
        iter_label = QLabel("Max Iterations:")
        iter_label.setStyleSheet(label_style_sheet)
        iter_header_hbox.addWidget(self.max_iter_checkbox)
        iter_header_hbox.addWidget(iter_label)
        max_iter_vbox.addLayout(iter_header_hbox)

        self.max_iter_input = QLineEdit("100")
        self.max_iter_input.setValidator(StrictIntValidator(1, 1_000_000))
        self.max_iter_input.setStyleSheet(
            "background-color: white; color: black; border: 1px solid #bdc3c7; padding: 5px;")
        self.max_iter_input.setToolTip("Maximum number of generations (recommended: 50-200)")
        max_iter_vbox.addWidget(self.max_iter_input)

        self.max_iter_checkbox.toggled.connect(self.max_iter_input.setEnabled)

        # Max Evaluations
        max_evals_vbox = QVBoxLayout()
        evals_header_hbox = QHBoxLayout()
        evals_header_hbox.setSpacing(2)
        evals_header_hbox.setContentsMargins(0, 0, 0, 0)
        evals_header_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.max_evals_checkbox = CheckBox()
        self.max_evals_checkbox.setChecked(False)
        evals_label = QLabel("Max Evaluations:")
        evals_label.setStyleSheet(label_style_sheet)
        evals_header_hbox.addWidget(self.max_evals_checkbox)
        evals_header_hbox.addWidget(evals_label)
        max_evals_vbox.addLayout(evals_header_hbox)

        self.max_evals_input = QLineEdit("10000")
        self.max_evals_input.setValidator(StrictIntValidator(1, 100_000_000))
        self.max_evals_input.setEnabled(False)
        self.max_evals_input.setStyleSheet(
            "background-color: white; color: black; border: 1px solid #bdc3c7; padding: 5px;")
        self.max_evals_input.setToolTip(
            "Maximum number of fitness function evaluations (nFES)\n"
            "Useful for comparing algorithms fairly, since algorithms\n"
            "may use a different number of evaluations per iteration")
        max_evals_vbox.addWidget(self.max_evals_input)

        self.max_evals_checkbox.toggled.connect(self.max_evals_input.setEnabled)

        algo_hbox.addLayout(algorithm_vbox)
        algo_hbox.addLayout(pop_size_vbox)
        algo_hbox.addLayout(max_iter_vbox)
        algo_hbox.addLayout(max_evals_vbox)
        algo_vbox.addLayout(algo_hbox)

        # Differential Evolution Parameters
        self.de_sliders_hbox = QHBoxLayout()

        de_diff_vbox, self.diff_slider, self.diff_value_label = self.__create_slider(
            "Differential Weight (0 - 2.0):", 0, 200, 50, object_name="diff_label")
        de_cross_vbox, self.crossover_slider, self.crossover_value_label = self.__create_slider(
            "Crossover Probability (0 - 1.0):", 0, 100, 90, object_name="crossover_label")

        self.de_sliders_hbox.addLayout(de_diff_vbox)
        self.de_sliders_hbox.addLayout(de_cross_vbox)

        # Particle Swarm Optimization Parameters
        self.pso_sliders_vbox = QVBoxLayout()
        pso_sliders_hbox1 = QHBoxLayout()
        pso_sliders_hbox2 = QHBoxLayout()

        c1_vbox, self.c1_slider, self.c1_value_label = self.__create_slider(
            "c1 (0 - 4.0):", 0, 400, 200, object_name="pso_c1_label")
        c2_vbox, self.c2_slider, self.c2_value_label = self.__create_slider(
            "c2 (0 - 4.0):", 0, 400, 200, object_name="pso_c2_label")
        w_vbox, self.w_slider, self.w_value_label = self.__create_slider(
            "w (0.4 - 0.9):", 40, 90, 70, object_name="pso_w_label")
        min_velocity_vbox, self.min_velocity_slider, self.min_velocity_value_label = self.__create_slider(
            "Minimal Velocity (-3.0 - 0):", -300, 0, -150, object_name="pso_min_velocity_label")
        max_velocity_vbox, self.max_velocity_slider, self.max_velocity_value_label = self.__create_slider(
            "Maximal Velocity (0 - 3.0):", 0, 300, 150, object_name="pso_max_velocity_label")

        pso_sliders_hbox1.addLayout(c1_vbox)
        pso_sliders_hbox1.addLayout(c2_vbox)
        pso_sliders_hbox1.addLayout(w_vbox)
        pso_sliders_hbox2.addLayout(min_velocity_vbox)
        pso_sliders_hbox2.addLayout(max_velocity_vbox)
        self.pso_sliders_vbox.addLayout(pso_sliders_hbox1)
        self.pso_sliders_vbox.addLayout(pso_sliders_hbox2)

        # Genetic Algorithm Parameters
        self.ga_sliders_hbox = QHBoxLayout()

        ga_cross_vbox, self.ga_crossover_slider, self.ga_crossover_value_label = self.__create_slider(
            "Crossover Rate (0 - 1.0):", 0, 100, 25, object_name="ga_crossover_label")
        ga_mut_vbox, self.ga_mutation_slider, self.ga_mutation_value_label = self.__create_slider(
            "Mutation Rate (0 - 1.0):", 0, 100, 25, object_name="ga_mutation_label")

        self.ga_sliders_hbox.addLayout(ga_cross_vbox)
        self.ga_sliders_hbox.addLayout(ga_mut_vbox)

        # Bat Algorithm Parameters
        self.bat_sliders_vbox = QVBoxLayout()
        bat_sliders_hbox1 = QHBoxLayout()
        bat_sliders_hbox2 = QHBoxLayout()

        loud_vbox, self.loud_slider, self.loud_value_label = self.__create_slider(
            "Loudness (0 - 1.0):", 0, 100, 100, object_name="loud_label")
        ba_alpha_vbox, self.ba_alpha_slider, self.ba_alpha_value_label = self.__create_slider(
            "Alpha (0 - 1.0):", 0, 100, 97, object_name="ba_alpha_label")
        fmin_vbox, self.fmin_slider, self.fmin_value_label = self.__create_slider(
            "Frequency Min (0 - 2.0):", 0, 200, 0, object_name="fmin_label")
        pulse_vbox, self.pulse_slider, self.pulse_value_label = self.__create_slider(
            "Pulse Rate (0 - 1.0):", 0, 100, 100, object_name="pulse_label")
        ba_gamma_vbox, self.ba_gamma_slider, self.ba_gamma_value_label = self.__create_slider(
            "Gamma (0 - 1.0):", 0, 100, 10, object_name="ba_gamma_label")
        fmax_vbox, self.fmax_slider, self.fmax_value_label = self.__create_slider(
            "Frequency Max (0 - 2.0):", 0, 200, 200, object_name="fmax_label")

        self.fmin_slider.valueChanged.disconnect()
        self.fmax_slider.valueChanged.disconnect()

        self.fmin_slider.valueChanged.connect(lambda value: (
            self.fmin_value_label.setText(f"{value / 100:.2f}"),
            self.fmax_slider.setMinimum(value)
        ))
        self.fmax_slider.valueChanged.connect(lambda value: (
            self.fmax_value_label.setText(f"{value / 100:.2f}"),
            self.fmin_slider.setMaximum(value)
        ))

        bat_sliders_hbox1.addLayout(loud_vbox)
        bat_sliders_hbox1.addLayout(ba_alpha_vbox)
        bat_sliders_hbox1.addLayout(fmin_vbox)
        bat_sliders_hbox2.addLayout(pulse_vbox)
        bat_sliders_hbox2.addLayout(ba_gamma_vbox)
        bat_sliders_hbox2.addLayout(fmax_vbox)

        self.bat_sliders_vbox.addLayout(bat_sliders_hbox1)
        self.bat_sliders_vbox.addLayout(bat_sliders_hbox2)

        # Firefly Algorithm Parameters
        self.firefly_sliders_vbox = QVBoxLayout()
        firefly_sliders_hbox1 = QHBoxLayout()
        firefly_sliders_hbox2 = QHBoxLayout()

        fa_alpha_vbox, self.fa_alpha_slider, self.fa_alpha_value_label = self.__create_slider(
            "α (0 - 1.0):", 0, 100, 100, object_name="fa_alpha_label")
        beta_vbox, self.beta_slider, self.beta_value_label = self.__create_slider(
            "β₀ (0 - 2.0):", 0, 200, 100, object_name="beta_label")
        fa_gamma_vbox, self.fa_gamma_slider, self.fa_gamma_value_label = self.__create_slider(
            "γ (0 - 10.0):", 0, 1000, 1, object_name="fa_gamma_label")
        theta_vbox, self.theta_slider, self.theta_value_label = self.__create_slider(
            "θ (0 - 1.0):", 0, 100, 97, object_name="theta_label")

        firefly_sliders_hbox1.addLayout(fa_alpha_vbox)
        firefly_sliders_hbox1.addLayout(beta_vbox)
        firefly_sliders_hbox2.addLayout(fa_gamma_vbox)
        firefly_sliders_hbox2.addLayout(theta_vbox)

        self.firefly_sliders_vbox.addLayout(firefly_sliders_hbox1)
        self.firefly_sliders_vbox.addLayout(firefly_sliders_hbox2)

        algo_specific_hbox = QHBoxLayout()
        algo_specific_hbox.setContentsMargins(0, 10, 0, 0)

        algo_specific_hbox.addLayout(self.de_sliders_hbox)
        algo_specific_hbox.addLayout(self.pso_sliders_vbox)
        algo_specific_hbox.addLayout(self.ga_sliders_hbox)
        algo_specific_hbox.addLayout(self.bat_sliders_vbox)
        algo_specific_hbox.addLayout(self.firefly_sliders_vbox)

        algo_vbox.addLayout(algo_specific_hbox)
        algo_group.setLayout(algo_vbox)
        layout.addWidget(algo_group)
        layout.addStretch()

        self.__apply_no_scroll_filter()
        self.__set_data_squashing_settings_visibility(False)
        self.__hide_algorithm_settings_visibility()

    def __create_menu_bar(self):
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet(
            "QMenuBar { background-color: #34495e; color: white; }"
            "QMenuBar::item:selected { background-color: #2c3e50; }"
            "QMenu { background-color: white; color: black; }"
            "QMenu::item:selected { background-color: #3498db; color: white; }"
        )

        file_menu = menu_bar.addMenu("File")

        open_results_action = file_menu.addAction("Open saved results")
        open_results_action.setShortcut("Ctrl+O")
        open_results_action.triggered.connect(self.__open_saved_results)

        file_menu.addSeparator()

        export_pipeline_action = file_menu.addAction("Export Mining Pipeline")
        export_pipeline_action.triggered.connect(self.__export_pipeline)

        import_pipeline_action = file_menu.addAction("Import Mining Pipeline")
        import_pipeline_action.triggered.connect(self.__import_pipeline)

        file_menu.addSeparator()

        exit_action = file_menu.addAction("Exit")
        exit_action.setShortcut("Ctrl+W")
        exit_action.triggered.connect(self.close)

        help_menu = menu_bar.addMenu("Help")

        license_action = help_menu.addAction("License")
        license_action.triggered.connect(self.__show_license_dialog)

        help_menu.addSeparator()

        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.__show_about_dialog)

    def __create_tool_bar(self):
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #34495e;
                spacing: 10px;
                padding: 5px;
                border: none;
            }
            QToolBar QToolButton {
                background-color: #e74c3c;
                color: white;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QToolBar QToolButton:hover {
                background-color: #c0392b;
            }
            QToolBar QToolButton:pressed {
                background-color: #a93226;
            }
        """)

        run_action = QAction("▶️ Run Mining", self)
        run_action.triggered.connect(self.__run_mining)
        run_action.setShortcut("F5")  # Keyboard shortcut
        toolbar.addAction(run_action)

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

    def __create_separator(self):
        """Creates QFrame separator for separation of group boxes"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(
            "background-color: #bdc3c7; margin-left: 50px; margin-right: 50px; margin-top: 10px; margin-bottom: 10px;"
        )
        return separator

    def __create_group_box(self, title):
        """Creates QGroupBox with title for grouping sections of layout"""
        group_box = QGroupBox(title)

        group_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                color: #2c3e50;
                border: 2px solid #3498db;
                border-radius: 5px;
                margin-top: 20px;
                margin-bottom: 20px;
                margin-left: 50px;
                margin-right: 50px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 60px;
                top: 8px;
                padding: 0 5px;
            }
        """)

        return group_box

    def __create_slider(self, label_text: str, min_val: int, max_val: int, default_val: int, object_name: str = None):
        """Returns QVBoxLayout, QSlider, QLabel elements, where slider and label are placed inside vbox"""
        vbox = QVBoxLayout()

        label = QLabel(label_text)
        label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        if object_name:
            label.setObjectName(object_name)
        vbox.addWidget(label)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default_val)
        slider.setStyleSheet(
            "QSlider::groove:horizontal { background: #bdc3c7; height: 8px; border-radius: 4px; }"
            "QSlider::handle:horizontal { background: #3498db; width: 18px; height: 18px; border-radius: 9px; }"
        )
        vbox.addWidget(slider)

        value_label = QLabel(f"{default_val / 100:.2f}")
        value_label.setStyleSheet("color: #7f8c8d;")
        vbox.addWidget(value_label)

        slider.valueChanged.connect(
            lambda v, lbl=value_label: lbl.setText(f"{v / 100:.2f}")
        )

        return vbox, slider, value_label

    def __apply_no_scroll_filter(self):
        """Applies no scroll filter for combo boxes and sliders"""
        class NoScrollFilter(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.Wheel:
                    event.ignore()
                    return True
                return False

        scroll_filter = NoScrollFilter(self)

        for combo in self.findChildren(QComboBox):
            combo.installEventFilter(scroll_filter)
            combo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        for slider in self.findChildren(QSlider):
            slider.installEventFilter(scroll_filter)
            slider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def __open_saved_results(self):
        """Opens a new window with already saved mining results"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open saved results",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )

        if file_name is None or len(file_name) == 0:
            return

        for results_viewer in self.mining_results_viewer_list:
            if results_viewer.file_path == file_name and results_viewer.isVisible():
                QMessageBox.critical(self, "Error", f"The file {file_name} is already opened.")
                return

        self.statusBar().showMessage(f"Opening {os.path.basename(file_name)}...")
        QApplication.processEvents()

        viewer = MiningResultsViewer(file_path=file_name)
        if viewer.rules is not None and len(viewer.rules) > 0:
            self.mining_results_viewer_list.append(viewer)
            viewer.showMaximized()

        self.statusBar().showMessage(f"NiaARM GUI v1.0")

    def __export_pipeline_to_path(self, file_path: str):
        """Builds the pipeline configuration dict and writes it to a JSON file."""
        algo_name = self.algorithm_combo.currentText()

        algo_params = {}
        if algo_name == "Differential Evolution":
            algo_params = {
                "differential_weight": self.diff_slider.value() / 100,
                "crossover_probability": self.crossover_slider.value() / 100
            }
        elif algo_name == "Particle Swarm Optimization":
            algo_params = {
                "c1": self.c1_slider.value() / 100,
                "c2": self.c2_slider.value() / 100,
                "w": self.w_slider.value() / 100,
                "min_velocity": self.min_velocity_slider.value() / 100,
                "max_velocity": self.max_velocity_slider.value() / 100
            }
        elif algo_name == "Genetic Algorithm":
            algo_params = {
                "crossover_rate": self.ga_crossover_slider.value() / 100,
                "mutation_rate": self.ga_mutation_slider.value() / 100
            }
        elif algo_name == "Bat Algorithm":
            algo_params = {
                "loudness": self.loud_slider.value() / 100,
                "pulse_rate": self.pulse_slider.value() / 100,
                "alpha": self.ba_alpha_slider.value() / 100,
                "gamma": self.ba_gamma_slider.value() / 100,
                "min_frequency": self.fmin_slider.value() / 100,
                "max_frequency": self.fmax_slider.value() / 100
            }
        elif algo_name == "Firefly Algorithm":
            algo_params = {
                "alpha": self.fa_alpha_slider.value() / 100,
                "beta0": self.beta_slider.value() / 100,
                "gamma": self.fa_gamma_slider.value() / 100,
                "theta": self.theta_slider.value() / 100
            }

        pipeline = {
            "version": "1.0",
            "dataset": {
                "path": self.csv_input.text()
            },
            "data_squashing": {
                "enabled": self.data_squash_combo.currentText() == "Yes",
                "similarity": self.similarity_combo.currentText(),
                "threshold": float(self.ds_threshold_value_label.text())
            },
            "metrics": {
                metric: {
                    "enabled": check.isChecked(),
                    "weight": slider.value() / 100
                }
                for metric, (check, slider, _) in self.metric_sliders.items()
            },
            "algorithm": {
                "name": algo_name,
                "population_size": int(self.pop_size_input.text()),
                "max_iterations": int(self.max_iter_input.text()) if self.max_iter_checkbox.isChecked() else None,
                "max_evaluations": int(self.max_evals_input.text()) if self.max_evals_checkbox.isChecked() else None,
                "parameters": algo_params
            }
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(pipeline, f, indent=4)

    def __export_pipeline(self):
        """Opens a save dialog and exports the current configuration to JSON."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Mining Pipeline", "", "JSON Files (*.json);;All Files (*)")

        if not file_path:
            return
        if not file_path.endswith(".json"):
            file_path += ".json"

        try:
            self.__export_pipeline_to_path(file_path)
            self.statusBar().showMessage(f"Pipeline exported: {file_path}", 5000)
            QMessageBox.information(self, "Success", f"Pipeline saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export pipeline:\n{str(e)}")

    def __import_pipeline_from_path(self, file_path: str):
        """Reads a JSON pipeline file and applies its configuration to the UI."""
        with open(file_path, "r", encoding="utf-8") as f:
            pipeline = json.load(f)

        # Dataset
        csv_path = pipeline.get("dataset", {}).get("path", "")
        if csv_path and os.path.exists(csv_path):
            self.csv_input.setText(csv_path)
        elif csv_path:
            QMessageBox.warning(
                self, "Warning",
                f"Dataset file not found:\n{csv_path}\n\n"
                "All other settings have been applied."
            )

        # Data squashing
        ds = pipeline.get("data_squashing", {})
        self.data_squash_combo.setCurrentText("Yes" if ds.get("enabled") else "No")
        self.similarity_combo.setCurrentText(ds.get("similarity", "Euclidean"))
        threshold = ds.get("threshold", 0.5)
        pos = self.__threshold_to_slider(threshold)
        self.ds_threshold_slider.setValue(pos)

        # Metrics
        for metric, values in pipeline.get("metrics", {}).items():
            if metric in self.metric_sliders:
                check, slider, _ = self.metric_sliders[metric]
                check.setChecked(values.get("enabled", False))
                slider.setValue(int(values.get("weight", 0.5) * 100))

        # Algorithm
        algo = pipeline.get("algorithm", {})
        self.algorithm_combo.setCurrentText(algo.get("name", "Select Algorithm"))
        self.pop_size_input.setText(str(algo.get("population_size", 50)))
        max_iterations = algo.get("max_iterations")
        max_evaluations = algo.get("max_evaluations")

        self.max_iter_checkbox.setChecked(max_iterations is not None)
        self.max_iter_input.setText(str(max_iterations if max_iterations is not None else 100))

        self.max_evals_checkbox.setChecked(max_evaluations is not None)
        self.max_evals_input.setText(str(max_evaluations if max_evaluations is not None else 10000))

        params = algo.get("parameters", {})
        algo_name = algo.get("name", "")

        if algo_name == "Differential Evolution":
            self.diff_slider.setValue(int(params.get("differential_weight", 0.5) * 100))
            self.crossover_slider.setValue(int(params.get("crossover_probability", 0.9) * 100))
        elif algo_name == "Particle Swarm Optimization":
            self.c1_slider.setValue(int(params.get("c1", 2.0) * 100))
            self.c2_slider.setValue(int(params.get("c2", 2.0) * 100))
            self.w_slider.setValue(int(params.get("w", 0.7) * 100))
            self.min_velocity_slider.setValue(int(params.get("min_velocity", -1.5) * 100))
            self.max_velocity_slider.setValue(int(params.get("max_velocity", 1.5) * 100))
        elif algo_name == "Genetic Algorithm":
            self.ga_crossover_slider.setValue(int(params.get("crossover_rate", 0.25) * 100))
            self.ga_mutation_slider.setValue(int(params.get("mutation_rate", 0.25) * 100))
        elif algo_name == "Bat Algorithm":
            self.loud_slider.setValue(int(params.get("loudness", 1.0) * 100))
            self.pulse_slider.setValue(int(params.get("pulse_rate", 1.0) * 100))
            self.ba_alpha_slider.setValue(int(params.get("alpha", 0.97) * 100))
            self.ba_gamma_slider.setValue(int(params.get("gamma", 0.1) * 100))
            self.fmin_slider.setValue(int(params.get("min_frequency", 0.0) * 100))
            self.fmax_slider.setValue(int(params.get("max_frequency", 2.0) * 100))
        elif algo_name == "Firefly Algorithm":
            self.fa_alpha_slider.setValue(int(params.get("alpha", 1.0) * 100))
            self.beta_slider.setValue(int(params.get("beta0", 1.0) * 100))
            self.fa_gamma_slider.setValue(int(params.get("gamma", 0.01) * 100))
            self.theta_slider.setValue(int(params.get("theta", 0.97) * 100))

    def __import_pipeline(self):
        """Opens a load dialog and imports a mining pipeline from JSON."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Mining Pipeline", "", "JSON Files (*.json);;All Files (*)")

        if not file_path:
            return

        try:
            self.__import_pipeline_from_path(file_path)
            self.statusBar().showMessage(f"Pipeline imported: {file_path}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import pipeline:\n{str(e)}")

    def __show_license_dialog(self):
        QMessageBox.information(
            self,
            "License",
            "MIT License\n"
            "Copyright (c) 2026 Dario Zadravec\n\n"
            "Permission is hereby granted, free of charge, to any person obtaining a copy "
            "of this software and associated documentation files (the \"Software\"), to deal "
            "in the Software without restriction, including without limitation the rights "
            "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell "
            "copies of the Software, and to permit persons to whom the Software is "
            "furnished to do so, subject to the following conditions:\n\n"
            "The above copyright notice and this permission notice shall be included in all "
            "copies or substantial portions of the Software.\n\n"
            "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR "
            "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, "
            "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE"
            "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER"
            "LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,"
            "OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE"
            "SOFTWARE."
        )

    def __show_about_dialog(self):
        QMessageBox.information(
            self,
            "About NiaARM GUI",
            "NiaARM GUI\n"
            "Version 1.0\n\n"
            "This graphical user interface was developed using the PyQt6 framework "
            "for numerical association rule mining.\n\n"
            "Developed as a thesis project by:\n"
            "Dario Zadravec\n\n"
            "Under the supervision of:\n"
            "Iztok Fister Jr.\n"
            "Tilen Hliš\n\n"
            "University of Maribor\n"
            "Faculty of Electrical Engineering and Computer Science\n"
            "2026"
        )

    def __select_csv(self):
        """Gets CSV file containing a dataset"""
        if self.csv_editor is not None and self.csv_editor.isVisible():
            QMessageBox.critical(self,
                "Error",
                "CSV editor window is still opened.\nPlease close the window before changing CSV dataset."
            )
            return

        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select CSV file", "", "CSV Files (*.csv)"
        )

        if not file_name:
            return

        delimiter = self.__detect_csv_delimiter(file_name)

        # If delimiter is NOT comma, ask user for conversion
        if delimiter != ',':
            # Show modal dialog
            reply = QMessageBox.question(
                self,
                "Incorrect format of the CSV file",
                f"Selected CSV file doesn't use comma(,) for data separation.\n\n"
                f"NiaARM demands the use of comma as a data separator.\n\n"
                f"Do you want to convert your file to the correct format?\n"
                f"(New file will be saved with '_comma' in the file name)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Generate new filename
                base_path = os.path.dirname(file_name)
                base_name = os.path.basename(file_name)
                name_without_ext, ext = os.path.splitext(base_name)

                # New filename: original_name_comma.csv
                new_file_name = os.path.join(base_path, f"{name_without_ext}_comma{ext}")

                # Convert delimiter
                success = self.__convert_csv_delimiter(file_name, new_file_name, delimiter)

                if success:
                    # Use converted file
                    self.csv_input.setText(new_file_name)
                    self.statusBar().showMessage(
                        f"CSV converted: {os.path.basename(new_file_name)}",
                        5000
                    )

                    QMessageBox.information(
                        self,
                        "Successfully converted",
                        f"CSV file was successfully converted.\n\n"
                        f"New file: {os.path.basename(new_file_name)}\n\n"
                        f"File uses comma (,) as a separator."
                    )
                else:
                    # Conversion failed, clear input
                    self.csv_input.setText("")
            else:
                # User clicked No
                self.csv_input.setText("")
                self.statusBar().showMessage("CSV file was not selected", 3000)
        else:
            # Delimiter is already comma, proceed normally
            self.csv_input.setText(file_name)
            self.statusBar().showMessage(
                f"Dataset selected: {os.path.basename(file_name)}",
                3000
            )

    def __view_csv(self):
        """Opens a new window containing a CSV dataset for viewing/editing"""
        csv_path = self.csv_input.text()

        if csv_path == "":
            QMessageBox.critical(self, "Error", f"No CSV file has been selected")
            return
        elif self.csv_editor is not None and self.csv_editor.isVisible():
            QMessageBox.critical(self, "Error", f"CSV editor window is already opened")
            return

        file_name = os.path.basename(csv_path)
        self.statusBar().showMessage(f"Opening {file_name}...")
        QApplication.processEvents()

        self.csv_editor = CsvEditorWindow(csv_path=csv_path)
        self.csv_editor.show()
        self.statusBar().showMessage(f"NiaARM GUI v1.0")

    def __show_dataset_info(self):
        csv_path = self.csv_input.text()
        if not csv_path:
            QMessageBox.critical(self, "Error", "No CSV file has been selected")
            return
        try:
            dialog = DatasetInfoDialog(csv_path, parent=self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read dataset:\n{str(e)}")

    def __detect_csv_delimiter(self, file_path):
        """
        Automatically detects CSV delimiter (comma, semicolon, tab, pipe, etc.)
        Returns the detected delimiter or ',' as default
        """
        with open(file_path, 'r', encoding='utf-8') as file:
            # Read first 5 lines for detection
            sample = ''.join([file.readline() for _ in range(5)])

            # Use CSV Sniffer to detect delimiter
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter

            return delimiter

    def __convert_csv_delimiter(self, input_path, output_path, original_delimiter):
        """
        Converts CSV file from original delimiter to comma delimiter.
        Saves as new CSV file.
        """
        try:
            # Read CSV with original delimiter
            df = pd.read_csv(input_path, sep=original_delimiter, encoding='utf-8')

            # Write CSV with comma delimiter
            df.to_csv(output_path, index=False, sep=',', encoding='utf-8')

            return True

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error while converting CSV file",
                f"CSV file conversion didn't work.\n\n"
                f"Error: {str(e)}"
            )
            return False

    def __slider_to_threshold(self, pos):
        if pos <= 2:
            value = 10 ** (pos - 5)  # 0.00001, 0.0001, 0.001
            decimals = 5 - pos
        elif pos <= 101:
            value = round((pos - 2) * 0.01, 2)  # 0.01 do 0.99
            decimals = 2
        else:
            decimals = pos - 99  # 3, 4, 5
            value = round(1 - 10 ** (-decimals), decimals)  # 0.999, 0.9999, 0.99999
        return value, decimals

    def __threshold_to_slider(self, value: float) -> int:
        """Converts threshold value back to slider position"""
        if value <= 0.001:
            return max(0, round(value * 100000) - 1)
        elif value < 0.01:
            return 1
        elif value == 0.001:
            return 2
        elif value <= 0.99:
            return round(value * 100) + 2
        elif value >= 0.99999:
            return 104
        elif value >= 0.9999:
            return 103
        elif value >= 0.999:
            return 102
        else:
            return 101

    def __set_data_squashing_settings_visibility(self, value):
        self.similarity_label.setVisible(value)
        self.similarity_combo.setVisible(value)
        self.threshold_label.setVisible(value)
        self.ds_threshold_slider.setVisible(value)
        self.ds_threshold_value_label.setVisible(value)

    def __update_data_squashing_settings_visibility(self):
        selected_value = self.data_squash_combo.currentText()

        if selected_value == "Yes":
            self.__set_data_squashing_settings_visibility(True)
        else:
            self.__set_data_squashing_settings_visibility(False)

    def __hide_algorithm_settings_visibility(self):
        # DE
        self.diff_slider.setVisible(False)
        self.diff_value_label.setVisible(False)
        self.crossover_slider.setVisible(False)
        self.crossover_value_label.setVisible(False)
        self.findChild(QLabel, "diff_label").setVisible(False)
        self.findChild(QLabel, "crossover_label").setVisible(False)
        # PSO
        self.c1_slider.setVisible(False)
        self.c1_value_label.setVisible(False)
        self.c2_slider.setVisible(False)
        self.c2_value_label.setVisible(False)
        self.w_slider.setVisible(False)
        self.w_value_label.setVisible(False)
        self.min_velocity_slider.setVisible(False)
        self.min_velocity_value_label.setVisible(False)
        self.max_velocity_slider.setVisible(False)
        self.max_velocity_value_label.setVisible(False)
        self.findChild(QLabel, "pso_c1_label").setVisible(False)
        self.findChild(QLabel, "pso_c2_label").setVisible(False)
        self.findChild(QLabel, "pso_w_label").setVisible(False)
        self.findChild(QLabel, "pso_min_velocity_label").setVisible(False)
        self.findChild(QLabel, "pso_max_velocity_label").setVisible(False)
        # GA
        self.ga_crossover_slider.setVisible(False)
        self.ga_crossover_value_label.setVisible(False)
        self.ga_mutation_slider.setVisible(False)
        self.ga_mutation_value_label.setVisible(False)
        self.findChild(QLabel, "ga_crossover_label").setVisible(False)
        self.findChild(QLabel, "ga_mutation_label").setVisible(False)
        # BA
        self.loud_slider.setVisible(False)
        self.loud_value_label.setVisible(False)
        self.pulse_slider.setVisible(False)
        self.pulse_value_label.setVisible(False)
        self.ba_alpha_slider.setVisible(False)
        self.ba_alpha_value_label.setVisible(False)
        self.ba_gamma_slider.setVisible(False)
        self.ba_gamma_value_label.setVisible(False)
        self.fmin_slider.setVisible(False)
        self.fmin_value_label.setVisible(False)
        self.fmax_slider.setVisible(False)
        self.fmax_value_label.setVisible(False)
        self.findChild(QLabel, "loud_label").setVisible(False)
        self.findChild(QLabel, "pulse_label").setVisible(False)
        self.findChild(QLabel, "ba_alpha_label").setVisible(False)
        self.findChild(QLabel, "ba_gamma_label").setVisible(False)
        self.findChild(QLabel, "fmin_label").setVisible(False)
        self.findChild(QLabel, "fmax_label").setVisible(False)
        # FA
        self.fa_alpha_slider.setVisible(False)
        self.fa_alpha_value_label.setVisible(False)
        self.beta_slider.setVisible(False)
        self.beta_value_label.setVisible(False)
        self.fa_gamma_slider.setVisible(False)
        self.fa_gamma_value_label.setVisible(False)
        self.theta_slider.setVisible(False)
        self.theta_value_label.setVisible(False)
        self.findChild(QLabel, "fa_alpha_label").setVisible(False)
        self.findChild(QLabel, "beta_label").setVisible(False)
        self.findChild(QLabel, "fa_gamma_label").setVisible(False)
        self.findChild(QLabel, "theta_label").setVisible(False)

    def __update_algorithm_settings_visibility(self):
        selected_algorithm = self.algorithm_combo.currentText()

        self.__hide_algorithm_settings_visibility()

        if selected_algorithm == "Differential Evolution":
            self.diff_slider.setVisible(True)
            self.diff_value_label.setVisible(True)
            self.crossover_slider.setVisible(True)
            self.crossover_value_label.setVisible(True)
            self.findChild(QLabel, "diff_label").setVisible(True)
            self.findChild(QLabel, "crossover_label").setVisible(True)
        elif selected_algorithm == "Particle Swarm Optimization":
            self.c1_slider.setVisible(True)
            self.c1_value_label.setVisible(True)
            self.c2_slider.setVisible(True)
            self.c2_value_label.setVisible(True)
            self.w_slider.setVisible(True)
            self.w_value_label.setVisible(True)
            self.min_velocity_slider.setVisible(True)
            self.min_velocity_value_label.setVisible(True)
            self.max_velocity_slider.setVisible(True)
            self.max_velocity_value_label.setVisible(True)
            self.findChild(QLabel, "pso_c1_label").setVisible(True)
            self.findChild(QLabel, "pso_c2_label").setVisible(True)
            self.findChild(QLabel, "pso_w_label").setVisible(True)
            self.findChild(QLabel, "pso_min_velocity_label").setVisible(True)
            self.findChild(QLabel, "pso_max_velocity_label").setVisible(True)
        elif selected_algorithm == "Genetic Algorithm":
            self.ga_crossover_slider.setVisible(True)
            self.ga_crossover_value_label.setVisible(True)
            self.ga_mutation_slider.setVisible(True)
            self.ga_mutation_value_label.setVisible(True)
            self.findChild(QLabel, "ga_crossover_label").setVisible(True)
            self.findChild(QLabel, "ga_mutation_label").setVisible(True)
        elif selected_algorithm == "Bat Algorithm":
            self.loud_slider.setVisible(True)
            self.loud_value_label.setVisible(True)
            self.pulse_slider.setVisible(True)
            self.pulse_value_label.setVisible(True)
            self.ba_alpha_slider.setVisible(True)
            self.ba_alpha_value_label.setVisible(True)
            self.ba_gamma_slider.setVisible(True)
            self.ba_gamma_value_label.setVisible(True)
            self.fmin_slider.setVisible(True)
            self.fmin_value_label.setVisible(True)
            self.fmax_slider.setVisible(True)
            self.fmax_value_label.setVisible(True)
            self.findChild(QLabel, "loud_label").setVisible(True)
            self.findChild(QLabel, "pulse_label").setVisible(True)
            self.findChild(QLabel, "ba_alpha_label").setVisible(True)
            self.findChild(QLabel, "ba_gamma_label").setVisible(True)
            self.findChild(QLabel, "fmin_label").setVisible(True)
            self.findChild(QLabel, "fmax_label").setVisible(True)
        elif selected_algorithm == "Firefly Algorithm":
            self.fa_alpha_slider.setVisible(True)
            self.fa_alpha_value_label.setVisible(True)
            self.beta_slider.setVisible(True)
            self.beta_value_label.setVisible(True)
            self.fa_gamma_slider.setVisible(True)
            self.fa_gamma_value_label.setVisible(True)
            self.theta_slider.setVisible(True)
            self.theta_value_label.setVisible(True)
            self.findChild(QLabel, "fa_alpha_label").setVisible(True)
            self.findChild(QLabel, "beta_label").setVisible(True)
            self.findChild(QLabel, "fa_gamma_label").setVisible(True)
            self.findChild(QLabel, "theta_label").setVisible(True)

    def __get_selected_metrics(self):
        """Gets metrics selected in metrics table"""
        selected = {}
        for metric, (check, slider, label) in self.metric_sliders.items():
            if check.isChecked():
                if str(metric) == "RHS Support":
                    selected["rhs_support"] = float(label.text())
                else:
                    selected[str(metric).lower()] = float(label.text())
        return selected

    def __get_selected_algorithm(self):
        """Gets algorithm selected in algorithm combo box"""
        algo = None
        pop_size = int(self.pop_size_input.text())

        if pop_size < 1:
            return algo

        if self.algorithm_combo.currentText() == "Differential Evolution":
            diff_weight = float(self.diff_value_label.text())
            cross_prob = float(self.crossover_value_label.text())
            algo = DifferentialEvolution(
                population_size=pop_size, differential_weight=diff_weight, crossover_probability=cross_prob
            )
        elif self.algorithm_combo.currentText() == "Particle Swarm Optimization":
            c1 = float(self.c1_value_label.text())
            c2 = float(self.c2_value_label.text())
            w = float(self.w_value_label.text())
            min_velocity = float(self.min_velocity_value_label.text())
            max_velocity = float(self.max_velocity_value_label.text())
            algo = ParticleSwarmOptimization(
                population_size=pop_size, c1=c1, c2=c2, w=w,
                min_velocity=min_velocity, max_velocity=max_velocity
            )
        elif self.algorithm_combo.currentText() == "Genetic Algorithm":
            cross_rate = float(self.ga_crossover_value_label.text())
            mut_rate = float(self.ga_mutation_value_label.text())
            algo = GeneticAlgorithm(
                population_size=pop_size, crossover_rate=cross_rate, mutation_rate=mut_rate
            )
        elif self.algorithm_combo.currentText() == "Bat Algorithm":
            loudness = float(self.loud_value_label.text())
            pulse_rate = float(self.pulse_value_label.text())
            alpha = float(self.ba_alpha_value_label.text())
            gamma = float(self.ba_gamma_value_label.text())
            frequency_min = float(self.fmin_value_label.text())
            frequency_max = float(self.fmax_value_label.text())
            algo = BatAlgorithm(
                population_size=pop_size, loudness=loudness, pulse_rate=pulse_rate, alpha=alpha,
                gamma=gamma, min_frequency=frequency_min, max_frequency=frequency_max
            )
        elif self.algorithm_combo.currentText() == "Firefly Algorithm":
            alpha = float(self.fa_alpha_value_label.text())
            beta = float(self.beta_value_label.text())
            gamma = float(self.fa_gamma_value_label.text())
            theta = float(self.theta_value_label.text())
            algo = FireflyAlgorithm(
                population_size=pop_size, alpha=alpha, beta0=beta, gamma=gamma, theta=theta
            )

        return algo

    def __run_mining(self):
        """Executes numerical association rule mining on selected dataset"""
        if hasattr(self, 'mining_thread') and self.mining_thread.isRunning():
            QMessageBox.warning(self, "Warning",
                "A mining process is still finishing in the background. Please wait.")
            return

        if not os.path.exists(self.csv_input.text()):
            QMessageBox.critical(self, "Error", f"CSV file not found")
            return

        data = Dataset(self.csv_input.text())
        metrics = self.__get_selected_metrics()
        algo = self.__get_selected_algorithm()
        if not self.max_iter_checkbox.isChecked() and not self.max_evals_checkbox.isChecked():
            QMessageBox.critical(self, "Error",
                "At least one stopping criterion (Iterations or Function Evaluations) must be selected."
            )
            return

        max_iter = int(self.max_iter_input.text()) if self.max_iter_checkbox.isChecked() else math.inf
        max_eval = int(self.max_evals_input.text()) if self.max_evals_checkbox.isChecked() else math.inf

        if data is None or algo is None or len(metrics) < 1:
            QMessageBox.critical(self, "Error", f"Not all parameters have been selected")
            return

        loading_dialog = LoadingDialog("Starting process...", self)
        loading_dialog.show()
        QApplication.processEvents()

        squash_threshold = None
        squash_similarity = None
        if self.data_squash_combo.currentText() == "Yes":
            squash_threshold = float(self.ds_threshold_value_label.text())
            squash_similarity = self.similarity_combo.currentText().lower()

        self.mining_thread = MiningThread(data, algo, metrics, max_iter, max_eval, squash_threshold, squash_similarity)

        self.mining_thread.progress_update.connect(loading_dialog.set_text)
        self.mining_thread.squash_completed.connect(loading_dialog.set_squash_info)
        self.mining_thread.iteration_progress.connect(
            lambda i, mi, e, me: loading_dialog.progress_info_label.setText(
                f"Iteration {i} / {mi}" if mi != -1 else f"Function evaluations: {e} / {me}"
            )
        )
        self.mining_thread.finished.connect(
            lambda rules, run_time: self.__on_mining_finished(rules, run_time, loading_dialog))
        self.mining_thread.error.connect(lambda err: self.__on_mining_error(err, loading_dialog))

        loading_dialog.rejected.connect(lambda: self.__on_mining_cancelled(loading_dialog))

        self.mining_thread.start()

    def __on_mining_finished(self, rules, run_time, loading_dialog):
        """Calls when mining thread finishes"""
        loading_dialog.show_completed()
        loading_dialog.close()
        viewer = MiningResultsViewer(rules=rules, time=run_time)

        if len(viewer.rules) > 0:
            self.mining_results_viewer_list.append(viewer)
            viewer.showMaximized()
            self.showMinimized()

    def __on_mining_error(self, error_msg, loading_dialog):
        """Calls when mining thread error occurs"""
        loading_dialog.close()
        QMessageBox.critical(self, "Error", f"Mining failed:\n{error_msg}")

    def __on_mining_cancelled(self, loading_dialog):
        """Calls when user cancels mining"""
        if hasattr(self, 'mining_thread') and self.mining_thread.isRunning():
            self.mining_thread.cancel()
            loading_dialog.close()
            self.statusBar().showMessage(
                "Cancelling... mining will stop once the current step finishes", 5000)


class MiningThread(QThread):
    """Thread for mining, does not conflict with UI"""
    progress_update = pyqtSignal(str)
    squash_completed = pyqtSignal(int, int)
    iteration_progress = pyqtSignal(int, int, int, int)
    finished = pyqtSignal(object, float)
    error = pyqtSignal(str)

    def __init__(self, data, algo, metrics, max_iter, max_eval, squash_threshold=None, squash_similarity=None):
        super().__init__()
        self.data = data
        self.algo = algo
        self.metrics = metrics
        self.max_iter = max_iter
        self.max_eval = max_eval
        self.squash_threshold = squash_threshold
        self.squash_similarity = squash_similarity
        self._is_cancelled = False

    def cancel(self):
        """Sets cancellation flag"""
        self._is_cancelled = True

    def run(self):
        try:
            if self.squash_threshold is not None:
                self.progress_update.emit("Data squashing in progress...")
                original_size = len(self.data.transactions)
                self.data = squash(self.data, threshold=self.squash_threshold, similarity=self.squash_similarity)
                squashed_size = len(self.data.transactions)
                self.squash_completed.emit(original_size, squashed_size)

            if self._is_cancelled:
                self.error.emit("Mining cancelled by user")
                return

            self.progress_update.emit("Mining in progress...")

            problem = NiaARM(
                self.data.dimension, self.data.features, self.data.transactions,
                self.metrics, logging=True
            )
            task = Task(
                problem,
                max_evals=self.max_eval,
                max_iters=self.max_iter,
                optimization_type=OptimizationType.MAXIMIZATION
            )

            algorithm = self.algo
            if isinstance(algorithm, str):
                algorithm = get_algorithm(algorithm)

            algorithm.callbacks = ProgressCallback(self, task)

            start_time = time.perf_counter()
            xb, fxb = algorithm.run(task)
            stop_time = time.perf_counter()

            # algorithm.run() returns (None, None) on cancellation or exception
            if xb is None or self._is_cancelled:
                self.error.emit("Mining cancelled by user")
                return

            run_time = stop_time - start_time
            problem.rules.sort()

            self.finished.emit(problem.rules, run_time)
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))


class ProgressCallback(Callback):
    """Reports the current iteration and evaluation count via a Qt signal."""
    def __init__(self, mining_thread, task):
        super().__init__()
        self.mining_thread = mining_thread
        self._task = task

    def before_iteration(self, population, fitness, best_x, best_fitness, **params):
        super().before_iteration(population, fitness, best_x, best_fitness, **params)
        if self.mining_thread._is_cancelled:
            raise InterruptedError("Mining cancelled by user")

    def after_iteration(self, population, fitness, best_x, best_fitness, **params):
        super().after_iteration(population, fitness, best_x, best_fitness, **params)
        max_iters = self._task.max_iters
        max_evals = self._task.max_evals
        self.mining_thread.iteration_progress.emit(
            self._task.iters,
            -1 if max_iters == math.inf else int(max_iters),
            self._task.evals,
            -1 if max_evals == math.inf else int(max_evals)
        )