import numpy as np
import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIntValidator, QValidator
from PyQt6.QtWidgets import QTableWidgetItem
from niaarm import Rule


class LoadedRule(Rule):
    def __init__(self, antecedent, consequent, fitness, num_transactions, loaded_inclusion, loaded_amplitude,
                 full_count, antecedent_count, consequent_count, ant_not_con, con_not_ant, not_ant_not_con):
        super().__init__(antecedent, consequent, fitness)

        self.num_transactions = num_transactions
        self.full_count = full_count
        self.antecedent_count = antecedent_count
        self.consequent_count = consequent_count
        self.ant_not_con = ant_not_con
        self.con_not_ant = con_not_ant
        self.not_ant_not_con = not_ant_not_con

        self.loaded_inclusion = loaded_inclusion
        self.loaded_amplitude = loaded_amplitude

    @property
    def inclusion(self):
        """Override inclusion property"""
        return self.loaded_inclusion

    @property
    def amplitude(self):
        """Override amplitude property"""
        return self.loaded_amplitude


class NumericTableWidgetItem(QTableWidgetItem):
    """Formats the QTableWidgetItems with numerical values"""
    def __init__(self, value):
        if pd.isna(value) or np.isinf(value):
            super().__init__("")
            self.numeric_value = float("-inf")
        else:
            super().__init__(f"{float(value):.3f}")
            self.numeric_value = float(value)

        self.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def __lt__(self, other):
        """Defines how elements are sorted by numerical value"""
        if isinstance(other, NumericTableWidgetItem):
            return self.numeric_value < other.numeric_value
        return super().__lt__(other)


class StrictIntValidator(QIntValidator):
    """Validator for strict integers"""

    def validate(self, input_str, pos):
        if "." in input_str:
            return QValidator.State.Invalid, input_str, pos
        return super().validate(input_str, pos)